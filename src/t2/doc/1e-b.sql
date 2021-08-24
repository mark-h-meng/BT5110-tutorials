-- SELECT 	b.title FROM book b WHERE b.publisher='Wiley'; /* 25 row */

-- SELECT 	b.title, s.name AS ownername, d.faculty AS ownerfaculty
-- FROM book b, copy c, student s, department d 
-- WHERE b.publisher='Wiley' AND b.ISBN13=c.book AND c.owner=s.email AND s.department=d.department;
/* 100 row */

/*
SELECT b.title, s1.name AS ownername, d1.faculty AS ownerfaculty, 
	s2.name AS borrowername, d2.faculty AS borrowerfaculty
FROM book b, copy c, student s1, department d1,
	student s2, department d2, loan l
WHERE b.publisher='Wiley' AND b.ISBN13=c.book AND l.copy=c.copy AND c.book=l.book AND
	c.owner=s1.email AND s1.department=d1.department AND l.owner=c.owner AND
	l.borrower=s2.email AND s2.department=d2.department;
*/
/* 400 rows */

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