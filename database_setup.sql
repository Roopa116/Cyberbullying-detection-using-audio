CREATE DATABASE voiceshield_db;

USE voiceshield_db;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('user', 'admin') DEFAULT 'user'
);

CREATE TABLE predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    guest_id VARCHAR(255) NULL,
    audio_file VARCHAR(255) NOT NULL,
    transcribed_text TEXT NOT NULL,
    classification ENUM('Bullying', 'Not Bullying') NOT NULL,
    matched_keywords TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
