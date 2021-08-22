// "\! cls" to clear the screen

psql -U postgres -h localhost

create database abc;

\l

create user alice with password 'alice';

\c abc;

create table student (
	name VARCHAR(32),
	email VARCHAR(256) PRIMARY KEY,
	year DATE,
	faculty VARCHAR(62),
	department VARCHAR(32),
	graduate DATE,
	CHECK(graduate >= year)
);

\d students

\i 'C:\\Users\\mark\\Desktop\\NUNStAStudent.sql'

select * from student;

\c postgres
drop database 5110ABC;

\q