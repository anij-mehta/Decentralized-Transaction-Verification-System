DELIMITER $$

CREATE TRIGGER before_transaction_insert 
BEFORE INSERT ON Transactions
FOR EACH ROW
BEGIN
    DECLARE sender_balance DECIMAL(20,8);

    -- Check sender wallet balance
    SELECT balance INTO sender_balance FROM Wallets WHERE wallet_id = NEW.sender_wallet_id;
    
    IF sender_balance < NEW.amount THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Insufficient balance';
    END IF;

    -- Deduct balance from sender
    UPDATE Wallets SET balance = balance - NEW.amount WHERE wallet_id = NEW.sender_wallet_id;

    -- Add balance to receiver
    UPDATE Wallets SET balance = balance + NEW.amount WHERE wallet_id = NEW.receiver_wallet_id;

    -- Generate transaction hash
    SET NEW.transaction_hash = generate_hash(CONCAT(NEW.sender_wallet_id, NEW.receiver_wallet_id, NEW.amount, NEW.timestamp));
END$$

DELIMITER ;


DELIMITER $$

CREATE TRIGGER validate_transaction BEFORE INSERT ON Transactions
FOR EACH ROW
BEGIN
    DECLARE sender_exists INT;
    DECLARE receiver_exists INT;

    SELECT COUNT(*) INTO sender_exists FROM Wallets WHERE wallet_id = NEW.sender_wallet_id;
    SELECT COUNT(*) INTO receiver_exists FROM Wallets WHERE wallet_id = NEW.receiver_wallet_id;

    IF sender_exists = 0 OR receiver_exists = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid sender or receiver wallet';
    END IF;
END$$

DELIMITER ;

DELIMITER $$

CREATE TRIGGER after_transaction_update
AFTER UPDATE ON Transactions
FOR EACH ROW
BEGIN
    -- Update block size when a transaction is added to a block
    IF NEW.block_id IS NOT NULL AND OLD.block_id IS NULL THEN
        UPDATE Blocks 
        SET size = size + 1 
        WHERE block_id = NEW.block_id;
        
        -- Log the transaction confirmation
        INSERT INTO TransactionLogs (transaction_id, action, details)
        VALUES (NEW.transaction_id, 'confirmed', CONCAT('Added to block #', NEW.block_id));
        
        -- Update transaction status
        UPDATE Transactions 
        SET status = 'confirmed' 
        WHERE transaction_id = NEW.transaction_id;
        
        -- Create alerts for transaction participants
        -- For sender
        INSERT INTO Alerts (user_id, title, message)
        SELECT u.user_id, 'Transaction Confirmed', 
               CONCAT('Your transaction of ', NEW.amount, ' has been confirmed in block #', NEW.block_id)
        FROM Wallets w
        JOIN Users u ON w.user_id = u.user_id
        WHERE w.wallet_id = NEW.sender_wallet_id;
        
        -- For receiver
        INSERT INTO Alerts (user_id, title, message)
        SELECT u.user_id, 'Payment Received', 
               CONCAT('You received ', NEW.amount, ' in a transaction confirmed in block #', NEW.block_id)
        FROM Wallets w
        JOIN Users u ON w.user_id = u.user_id
        WHERE w.wallet_id = NEW.receiver_wallet_id;
    END IF;
END$$

DELIMITER ;

DELIMITER $$

CREATE TRIGGER before_transaction_insert 
BEFORE INSERT ON Transactions
FOR EACH ROW
BEGIN
    DECLARE sender_balance DECIMAL(20,8);
    DECLARE total_amount DECIMAL(20,8);

    -- Skip validation for mining rewards (system transactions)
    IF NEW.sender_wallet_id IS NOT NULL THEN
        -- Calculate total amount including fee
        SET total_amount = NEW.amount + COALESCE(NEW.fee, 0);
        
        -- Check sender wallet balance
        SELECT balance INTO sender_balance FROM Wallets WHERE wallet_id = NEW.sender_wallet_id;
        
        -- Validate sufficient balance
        IF sender_balance < total_amount THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Insufficient balance';
        END IF;

        -- Deduct balance from sender (including fee)
        UPDATE Wallets SET balance = balance - total_amount WHERE wallet_id = NEW.sender_wallet_id;
    END IF;

    -- Add balance to receiver (just the transaction amount, not the fee)
    IF NEW.receiver_wallet_id IS NOT NULL THEN
        UPDATE Wallets SET balance = balance + NEW.amount WHERE wallet_id = NEW.receiver_wallet_id;
    END IF;

    -- Set initial status
    SET NEW.status = 'pending';
    
    -- Generate transaction hash if not provided
    IF NEW.transaction_hash IS NULL OR NEW.transaction_hash = '' THEN
        SET NEW.transaction_hash = generate_hash(CONCAT(
            COALESCE(NEW.sender_wallet_id, 'system'),
            NEW.receiver_wallet_id,
            NEW.amount,
            NEW.timestamp,
            COALESCE(NEW.memo, '')
        ));
    END IF;
END$$

DELIMITER ;
