-- SHA-256 Hashing Function
CREATE FUNCTION generate_hash(input_string VARCHAR(255)) RETURNS VARCHAR(64) DETERMINISTIC
RETURN SHA2(input_string, 256);
