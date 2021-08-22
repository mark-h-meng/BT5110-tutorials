// "\! cls" (Windows) or "\! clear" (Mac/Ubuntu) to clear the screen

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

\d student

\i 'C:\\Users\\mark\\Desktop\\NUNStAStudent.sql'
// On Mac, you can just drag the file to the terminal. The command is like "abc=# \i /Users/mark/Documents/NUNStAStudent.sql"

select * from student;

\c postgres
drop database abc;

\q