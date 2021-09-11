import psycopg2
import os, sys
import csv
import logging

logging.basicConfig(filename='file_processing.log', filemode='w', level=logging.DEBUG)

question_pattern = ['/************',
                    '/*           ',
                    '/* Question ',
                    '/*           ', 
                    '/************']

match_pattern = [False, False, False, False, False]

curr_project = 0

'''
try:
    conn = psycopg2.connect("dbname='BT5110' user='postgres' host='localhost' password='admin'")
    cur = conn.cursor()
    cur.execute("""SELECT * FROM student;""")
    rows = cur.fetchall()
    print("\nShow me the databases:\n")
    for index, row in enumerate(rows):
        print(index, "\t", row)
except:
    print("I am unable to connect to the database")
'''
path = "C:\\Users\\mark\\Desktop\\answers(A0124294H).sql"

# The student no. should be extracted from the filename
student_no = 'A0124294H'

project = [['1.a',  '1.b', '1.c',  '1.d', '1.e',  '2']]
project_one = ['1.a',  '1.b', '1.c',  '1.d', '1.e',  '2']

file = open(path, 'r')
lines = file.readlines()
 
output_file = open("output.csv", "w")
# create the csv writer
writer = csv.writer(output_file)

header = ['student']
for qn in project_one:
    header.append(qn)
    header.append('comment')
    header.append('grade')

writer.writerow(header)
student_row = [student_no]

line_count = 0
pattern_index = 0
question_index = -1
solution_string = ''
# Strips the newline character
for line in lines:
    line_count += 1

    if False not in match_pattern:
        # increment question counting and reset match pattern
        pattern_index = 0
        match_pattern = [False, False, False, False, False]
        if question_index >= 0:
            student_row.append(solution_string)
            # Leave an empty cell for comments and grading
            student_row.append("") 
            student_row.append("")
            solution_string = ''
        question_index += 1
        logging.debug("SOLUTION OF " + project_one[question_index] + " IS SHOWN BELOW:")

    if line.startswith(question_pattern[pattern_index]):
        match_pattern[pattern_index] = True
        pattern_index += 1
    else:
        if len(line.strip()) > 0 and question_index >= 0:
            logging.info("Line{}: {}".format(line_count, line.strip()))
            solution_string += (line)
    #print("Line{}: {}".format(line_count, match_pattern))

writer.writerow(student_row)
output_file.close()
