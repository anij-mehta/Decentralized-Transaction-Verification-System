DELIMITER $$

CREATE PROCEDURE mine_block()
BEGIN
    DECLARE prev_block_hash VARCHAR(64);
    DECLARE new_block_hash VARCHAR(64);
    DECLARE mined_nonce INT DEFAULT 0;
    DECLARE curtime TIMESTAMP;
    DECLARE difficulty VARCHAR(4) DEFAULT '0000';

    -- Get the latest block hash
    SELECT block_hash INTO prev_block_hash FROM Blocks ORDER BY block_id DESC LIMIT 1;

    -- If there is no previous block, set a default value
    IF prev_block_hash IS NULL THEN
        SET prev_block_hash = '0000000000000000000000000000000000000000000000000000000000000000';
    END IF;

    SET curtime = NOW();

    -- Simulated Proof-of-Work loop
    REPEAT
        SET new_block_hash = generate_hash(CONCAT(prev_block_hash, mined_nonce, curtime));

        -- Check if the block meets the difficulty requirement
        IF LEFT(new_block_hash, 4) = difficulty THEN
            LEAVE;
        ELSE
            SET mined_nonce = mined_nonce + 1;
        END IF;
    UNTIL FALSE END REPEAT;

    -- Insert new block
    INSERT INTO Blocks (block_hash, previous_block_id, timestamp, nonce) 
    VALUES (new_block_hash, (SELECT MAX(block_id) FROM Blocks), curtime, mined_nonce);
    
END$$

DELIMITER ;

DELIMITER $$

CREATE PROCEDURE make_transaction(
    IN sender_username VARCHAR(100),
    IN receiver_username VARCHAR(100),
    IN amount DECIMAL(20,8)
)
BEGIN
    DECLARE sender_wallet_id INT;
    DECLARE receiver_wallet_id INT;
    
    -- Get sender wallet ID
    SELECT wallet_id INTO sender_wallet_id FROM Wallets WHERE user_id = (SELECT user_id FROM Users WHERE name = sender_username) LIMIT 1;
    
    -- Get receiver wallet ID
    SELECT wallet_id INTO receiver_wallet_id FROM Wallets WHERE user_id = (SELECT user_id FROM Users WHERE name = receiver_username) LIMIT 1;

    -- Insert transaction
    INSERT INTO Transactions (block_id, amount, sender_wallet_id, receiver_wallet_id, timestamp, transaction_hash)
    VALUES (NULL, amount, sender_wallet_id, receiver_wallet_id, NOW(), SHA2(CONCAT(sender_wallet_id, receiver_wallet_id, amount, NOW()), 256));
    
    COMMIT;
END$$

DELIMITER ;

DELIMITER $$

CREATE PROCEDURE mine_block(IN force_difficulty VARCHAR(5))
BEGIN
    DECLARE prev_block_hash VARCHAR(64);
    DECLARE new_block_hash VARCHAR(64);
    DECLARE mined_nonce INT DEFAULT 0;
    DECLARE curtime TIMESTAMP;
    DECLARE difficulty VARCHAR(5);
    DECLARE block_count INT;
    DECLARE avg_mining_time INT;
    
    -- Get current block count
    SELECT COUNT(*) INTO block_count FROM Blocks;
    
    -- Calculate appropriate difficulty based on blockchain size
    -- This provides automatic difficulty adjustment
    IF force_difficulty IS NOT NULL THEN
        SET difficulty = force_difficulty;
    ELSE
        -- Determine difficulty dynamically
        IF block_count < 100 THEN
            SET difficulty = '0000';  -- Easy
        ELSEIF block_count < 1000 THEN
            SET difficulty = '00000'; -- Medium
        ELSE
            SET difficulty = '000000'; -- Hard
        END IF;
    END IF;

    -- Get the latest block hash
    SELECT block_hash INTO prev_block_hash FROM Blocks ORDER BY block_id DESC LIMIT 1;

    -- If there is no previous block, set a default value
    IF prev_block_hash IS NULL THEN
        SET prev_block_hash = '0000000000000000000000000000000000000000000000000000000000000000';
    END IF;

    SET curtime = NOW();

    -- Simulated Proof-of-Work loop (improved for performance)
    REPEAT
        SET new_block_hash = generate_hash(CONCAT(prev_block_hash, mined_nonce, curtime));

        -- Check if the block meets the difficulty requirement
        IF LEFT(new_block_hash, LENGTH(difficulty)) = difficulty THEN
            LEAVE;
        ELSE
            SET mined_nonce = mined_nonce + 1;
        END IF;
        
        -- Safety exit for infinite loop prevention
        IF mined_nonce > 10000 THEN
            -- If we exceed 10000 attempts, reduce difficulty temporarily
            SET difficulty = LEFT(difficulty, LENGTH(difficulty) - 1);
            SET mined_nonce = 0;
        END IF;
    UNTIL FALSE END REPEAT;

    -- Insert new block
    INSERT INTO Blocks (block_hash, previous_block_id, timestamp, nonce, difficulty) 
    VALUES (new_block_hash, (SELECT MAX(block_id) FROM Blocks), curtime, mined_nonce, difficulty);
    
    -- Process pending transactions (up to 10 per block)
    UPDATE Transactions 
    SET block_id = LAST_INSERT_ID()
    WHERE block_id IS NULL
    ORDER BY timestamp
    LIMIT 10;
    
END$$

DELIMITER ;

DELIMITER $$

CREATE PROCEDURE make_transaction(
    IN sender_username VARCHAR(100),
    IN receiver_username VARCHAR(100),
    IN amount DECIMAL(20,8),
    IN memo VARCHAR(255)
)
BEGIN
    DECLARE sender_wallet_id INT;
    DECLARE receiver_wallet_id INT;
    DECLARE transaction_fee DECIMAL(20,8);
    DECLARE sender_user_id INT;
    DECLARE receiver_user_id INT;
    DECLARE tx_hash VARCHAR(64);
    
    -- Set transaction fee (0.1% of transaction amount with minimum of 0.01)
    SET transaction_fee = GREATEST(amount * 0.001, 0.01);
    
    -- Start transaction
    START TRANSACTION;
    
    -- Get sender user ID
    SELECT user_id INTO sender_user_id 
    FROM Users 
    WHERE name = sender_username 
    LIMIT 1;
    
    -- Get receiver user ID
    SELECT user_id INTO receiver_user_id 
    FROM Users 
    WHERE name = receiver_username 
    LIMIT 1;
    
    -- Validate users exist
    IF sender_user_id IS NULL OR receiver_user_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid sender or receiver username';
        ROLLBACK;
    END IF;
    
    -- Get sender wallet ID
    SELECT wallet_id INTO sender_wallet_id 
    FROM Wallets 
    WHERE user_id = sender_user_id 
    ORDER BY balance DESC
    LIMIT 1;
    
    -- Get receiver wallet ID
    SELECT wallet_id INTO receiver_wallet_id 
    FROM Wallets 
    WHERE user_id = receiver_user_id 
    LIMIT 1;
    
    -- Validate wallets exist
    IF sender_wallet_id IS NULL OR receiver_wallet_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Wallet not found';
        ROLLBACK;
    END IF;
    
    -- Generate transaction hash
    SET tx_hash = SHA2(CONCAT(sender_wallet_id, receiver_wallet_id, amount, NOW(), RAND()), 256);
    
    -- Insert transaction
    INSERT INTO Transactions (block_id, amount, sender_wallet_id, receiver_wallet_id, timestamp, transaction_hash, fee, memo)
    VALUES (NULL, amount, sender_wallet_id, receiver_wallet_id, NOW(), tx_hash, transaction_fee, memo);
    
    -- Commit transaction
    COMMIT;
END$$

DELIMITER ;
DELIMITER $$

CREATE PROCEDURE distribute_mining_reward(IN miner_user_id INT)
BEGIN
    DECLARE miner_wallet_id INT;
    DECLARE block_count INT;
    DECLARE mining_reward DECIMAL(20,8);
    
    -- Get miner's wallet
    SELECT wallet_id INTO miner_wallet_id 
    FROM Wallets 
    WHERE user_id = miner_user_id 
    LIMIT 1;

    -- Calculate current mining reward (starts high and decreases over time)
    SELECT COUNT(*) INTO block_count FROM Blocks;
    SET mining_reward = 50 / POWER(2, FLOOR(block_count / 100000));
    
    -- Add reward to miner's wallet
    UPDATE Wallets 
    SET balance = balance + mining_reward 
    WHERE wallet_id = miner_wallet_id;
    
    -- Record reward as a system transaction
    INSERT INTO Transactions (block_id, amount, sender_wallet_id, receiver_wallet_id, timestamp, transaction_hash, fee, memo)
    VALUES (
        (SELECT MAX(block_id) FROM Blocks),
        mining_reward,
        NULL, -- System transaction (no sender)
        miner_wallet_id,
        NOW(),
        SHA2(CONCAT('mining_reward', miner_wallet_id, NOW()), 256),
        0,
        'Mining Reward'
    );
END$$

DELIMITER ;
