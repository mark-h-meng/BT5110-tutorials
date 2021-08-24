--SELECT book
--FROM loan WHERE returned ISNULL; /* 105 rows */

--SELECT s1.name AS ownername, s2.name AS borrowername FROM student s1, student s2, loan l 
--WHERE l.owner=s1.email AND l.borrower=s2.email AND l.returned ISNULL; /* 105 rows */

--SELECT b.title, s1.name AS ownername, s2.name AS borrowername 
--FROM student s1, student s2, loan l, copy c, book b 
--WHERE l.owner=s1.email AND l.borrower=s2.email AND l.returned ISNULL AND
--	l.copy=c.copy AND l.book=c.book AND c.book=b.ISBN13 AND c.owner=s1.email; /* 105 rows */


SELECT b.title, s1.name AS ownername, s2.name AS borrowername 
FROM student s1, student s2, loan l, copy c, book b 
WHERE l.owner=s1.email AND l.borrower=s2.email AND l.returned ISNULL AND
	l.copy=c.copy AND l.book=c.book AND c.book=b.ISBN13 AND c.owner=s1.email AND b.publisher='Wiley'; /* 10 rows */
	
/*
SELECT b.title, 
		s1.name AS ownername, 
		d1.faculty AS ownerfaculty, 
		s2.name AS borrowername, 
		d2.faculty AS  borrowerfaculty
		FROM loan l, book b,  copy c, 
		student s1, student s2, 
		department d1, department d2
		WHERE l.book=b.ISBN13
		AND c.book = l.book 
		AND c.copy = l.copy 
		AND c.owner = l.owner
		AND l.owner = s1.email
		AND l.borrower = s2.email
		AND s1.department = d1.department
		AND s2.department = d2.department
		AND b.publisher ='Wiley'
		AND l.returned ISNULL;
*/
/* 10 rows */