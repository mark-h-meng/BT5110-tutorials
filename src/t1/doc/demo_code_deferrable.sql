DROP TABLE IF EXISTS city;
DROP TABLE IF EXISTS country;

CREATE TABLE country (
	name VARCHAR(32) PRIMARY KEY
);

CREATE TABLE city (
	name VARCHAR(32) PRIMARY KEY, 
	country VARCHAR(32) REFERENCES country(name) ON DELETE CASCADE DEFERRABLE
);

BEGIN TRANSACTION; -- By default, set all constraints IMMEDIATE
INSERT INTO country VALUES ('indonesia'); 
INSERT INTO city VALUES ('jakarta','indonesia'); 
END TRANSACTION;

BEGIN TRANSACTION; -- By default, set all constraints IMMEDIATE
INSERT INTO city VALUES ('hanoi','vietnam'); 
INSERT INTO country VALUES ('vietnam'); 
END TRANSACTION;

BEGIN TRANSACTION;
SET CONSTRAINTS ALL DEFERRED;
INSERT INTO city VALUES ('penang','malaysia'); 
INSERT INTO country VALUES ('malaysia'); 
END TRANSACTION;

SELECT * FROM CITY;