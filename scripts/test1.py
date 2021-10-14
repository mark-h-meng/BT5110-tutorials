import re
import os
import random
import string
import csv
import logging
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT 

logging.basicConfig(filename='file_processing.log', filemode='w', level=logging.DEBUG)

dbname='test'
user='postgres'
password='admin'
host='localhost'

drop_all_temp_views = "SELECT 'DROP VIEW IF EXISTS ' || table_name || ';' "\
    "FROM information_schema.views WHERE table_schema"\
        " NOT IN ('pg_catalog', 'information_schema') AND table_name !~ '^pg_';"

ORIGINAL_PARAM_Q1F = 6
SPECIAL_PARAMS_Q1F = [7, 8, 16]

initialize_connection_command = "dbname='" + dbname + "' user='" + user + "' host='" + host + "' password='" + password + "'" 
initialize_connection_command_no_db = "user='" + user + "' host='" + host + "' password='" + password + "'" 

EXECUTE_QUERY = True
KEEP_LINE_BREAK = True

regex = re.compile(r'[\n\r\t]')

default_question_pattern = '/* Question '

def generate_randome_string(len=5):
    random_str = ''.join(random.choice(string.ascii_lowercase) for x in range(len))
    return random_str

# Given a list of files submitted by students, output the list of student IDs
def extract_student_id(filenames):
    if len(filenames) <= 0:
        return None
    sid_list = []
    file_list = []
    for filepath in filenames:
        file_dir, file_name = os.path.split(filepath)
        if 'answers(A' in file_name:
            startindex = file_name.find('answers(A') + 9
            sid = file_name[startindex - 1 : startindex + 8]
        elif 'answer(A' in file_name:
            startindex = file_name.find('answer(A') + 8
            sid = file_name[startindex - 1 : startindex + 8]
        else:
            sid = file_name.split('.sql')[0]
        sid_list.append(sid)
        file_list.append(filepath)
    
    return sid_list, file_list


# Retrieve all files for a specific project
def retrieve_all_submission_files(dirpath):
    files = os.listdir(dirpath)
    files_with_path = []
    for filename in files:
        if filename[-4:] == '.sql':
            full_path = os.path.join(dirpath, filename)
            files_with_path.append(full_path)
        else:
            print("Filename", filename, "Skipped")
    return files_with_path


# Extract student's anwser for each questions and save in a CSV file
def extract_student_answers(submission_files, project_questions, csv_format = ['comment', 'grade'], 
    question_pattern = default_question_pattern, output_file = 'output.csv'):
    if submission_files is not None:
        student_id_lst, student_file_lst = extract_student_id(submission_files)
    print(str(len(student_id_lst)) + " students ID extracted from " + str(len(student_file_lst)) + " files")
    # match pattern is a list of Boolean variables to indicate whether the file
    #   reader has found a beginning pattern of new question
    match_pattern = False

    output_file = open(output_file, "w", newline='', encoding="UTF-8")
    #output_file = open(output_file, "w", newline='')
    # create the csv writer
    writer = csv.writer(output_file)

    header = ['student']

    # We perform a special arrangement for the test 1 as for Q1(f) we are generating
    #  four variants and run them for outputs separately. 
    # [1/2] The header row needs to be added with corresponding items
    '''
    for qn in project_questions:
        header.append(qn)
        if EXECUTE_QUERY:
            header.append('output')
        for col in csv_format:
            header.append(col)
    '''
    
    for idx, qn in enumerate(project_questions):
        header.append(qn)
        if EXECUTE_QUERY:
            header.append('output')  
        if idx == 5:
            for param in SPECIAL_PARAMS_Q1F:
                header.append("option_[" + str(param) + "]")
                if EXECUTE_QUERY:
                    header.append('output')  
                  
        for col in csv_format:
            header.append(col)

    writer.writerow(header)

    total_num_files = len(student_file_lst)
    file_count = 1

    for index, item in enumerate(student_file_lst):
        curr_student_id = student_id_lst[index]
        student_row = [curr_student_id]
        print("[" + "{:.2%}".format(file_count/total_num_files) + "] Reading submission: " + curr_student_id, end = "")

        # Drop all views created by previous student
        if EXECUTE_QUERY:
            cmd_list = psql_execute_query(drop_all_temp_views, question="", question_index=0, time_out=100000)
            for cmd in cmd_list[0]:
                psql_execute_query(cmd[0], question="", question_index=0, time_out=100000)
                
        input_file = open(item, 'r', encoding="utf8")
        reader_lines = input_file.readlines()

        line_count = 0
        question_index = -1 # Each submission file always starts with student's info
        solution_string = ''

        extra_comment = ''
        within_comment_block = False
        
        ANSWER_Q7_START = False

        # Strips the newline character
        for line in reader_lines:
            line_count += 1

            if match_pattern:
                # increment question counting and reset match pattern
                match_pattern = False
                if question_index >= 0:
                    student_row.append(solution_string.strip())

                    extra_comment = perform_extra_checking(solution_string, question_index, extra_comment)

                    if EXECUTE_QUERY:
                        # rows = psql_execute_query(solution_string.replace('\n', ' '), question="("+project_questions[question_index]+")")
                        rows = psql_execute_query(solution_string, question="("+project_questions[question_index]+")", question_index=question_index)
                        student_row.append(summarize_sql_output(rows)) 

                        # We perform a special arrangement for the test 1 as for Q1(f) we are generating
                        #  four variants and run them for outputs separately. 
                        # [2/2] Generate variants of query, execute them and record outputs

                        if question_index == 5 and len(SPECIAL_PARAMS_Q1F) > 0:
                            
                            print('(', end = "")
                            for param in SPECIAL_PARAMS_Q1F:
                                solution_string_variant = solution_string.replace(str(ORIGINAL_PARAM_Q1F), str(param))
                                student_row.append(solution_string_variant.strip())
                                
                                # Drop all views created by previous student
                                cmd_list = psql_execute_query(drop_all_temp_views, question="", question_index=0, time_out=100000)
                                for cmd in cmd_list[0]:
                                    psql_execute_query(cmd[0], question="", question_index=0, time_out=100000)
                                rows_variant = psql_execute_query(solution_string_variant, question="("+project_questions[question_index]+")", question_index=question_index)
                                student_row.append(summarize_sql_output(rows_variant)) 
                                print('+', end = "")
                            print(')', end = "")

                    # Leave an empty cell for comments and/or grading                    
                    for col in csv_format:
                        student_row.append(extra_comment) 
                        extra_comment = ""
                    
                    extra_comment = ''
                    solution_string = ''
                print('.', end = "")
                question_index += 1
                logging.debug("SOLUTION OF " + project_questions[question_index] + " IS SHOWN BELOW:")

            if line.startswith(question_pattern):
                # Start reading the solution for the next question
                match_pattern = True
            else:
                # Continue reading the solution for the current question if the question_index is not -1
                if len(line.strip()) > 0 and question_index >= 0 and question_index < 7:
                    
                    if within_comment_block:
                        comment_loc_end = line.find('*/')
                        if comment_loc_end >= 0:
                            line_without_comment = line_without_comment[comment_loc_end + 2:]
                            within_comment_block = False
                        else:
                            line_without_comment = ''
                        line = line_without_comment
                    
                    else:
                        # Remove comments from line
                        comment_loc_start = line.find('/*')
                        if comment_loc_start >= 0:
                            comment_loc_end = line.find('*/')
                            if comment_loc_end > comment_loc_start:
                                line_without_comment = line[0:comment_loc_start] + line[comment_loc_end + 2:]
                            else: # The comment block is not going to be eneded within the line
                                line_without_comment = line[0:comment_loc_start]
                                within_comment_block = True
                            line = line_without_comment
                        
                        if line.find('--') >= 0:
                            line = ""

                        if KEEP_LINE_BREAK:
                            if len(line.strip()) == 0:
                                line = ""
                        else:
                            line = line.strip()

                
                    logging.info("Line{}: {}".format(line_count, line.strip().encode('utf-8')))

                    solution_string += line

                elif question_index == 7:
                    if ANSWER_Q7_START:
                        line = line.replace('/*','').replace('*/','')
                        if KEEP_LINE_BREAK:
                            if len(line.strip()) == 0:
                                line = ""
                        else:
                            line = line.strip()
                        logging.info("Line{}: {}".format(line_count, line.strip().encode('utf-8')))

                        solution_string += line
                    
                    if line.find('Write your answer in English below (between the comment markers):') > 0:
                        ANSWER_Q7_START = True

        student_row.append(solution_string.strip())
        
        extra_comment = perform_extra_checking(solution_string, question_index,extra_comment)
        
        if EXECUTE_QUERY:
        # while False: # leave the last question not been executed
            rows = psql_execute_query(solution_string, question="("+project_questions[question_index]+")", question_index=question_index)
            student_row.append(summarize_sql_output(rows)) 
        
        for col in csv_format:
            student_row.append(extra_comment) 
            extra_comment = ""
        
        writer.writerow(student_row)
        
        print('.')
        file_count += 1
    output_file.close()

def psql_execute_query(query, question="", question_index=0, time_out='10000'):
    # Special arrangement for Q2.(a), as discussed on 11/Oct/2021
    if question_index == 6:
        return psql_execute_schema_code(query, question, question_index)

    try:     
        rows = []
        if question_index >= 6:
            return rows
        if len(query.strip()) <= 0:
            return rows
        connect_command = initialize_connection_command + " options='-c statement_timeout=" + str(time_out) + "'"

        conn = psycopg2.connect(connect_command)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        try:
            cur.execute(query)
            conn.commit()
            
            rows.append(cur.fetchall())
        except psycopg2.Error as errorMsg:  
            conn.rollback()
        return rows
    except Exception as error:
        print("Database query error: ", error, question, end="")
        print("Exception TYPE:", type(error), question, end="")

def psql_execute_schema_code(query, question="", question_index=0, time_out='10000'):
    try:     
        rows = []
        if len(query.strip()) <= 0:
            return rows
        connect_command = initialize_connection_command_no_db + " options='-c statement_timeout=" + str(time_out) + "'"

        conn = psycopg2.connect(connect_command)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        tmp_db_name = generate_randome_string(len=5)
        query_create_temp_db = "CREATE DATABASE " + tmp_db_name +";"
        connect_command_temp_db = initialize_connection_command_no_db + "dbname='" + tmp_db_name + "' options='-c statement_timeout=" + str(time_out) + "'"
        query_delete_temp_db = "DROP DATABASE " + tmp_db_name + ";"
        
        # step 1 create table 
        try:
            cur.execute(query_create_temp_db)
            conn.commit()
        except psycopg2.Error as errorMsg:  
            conn.rollback()
        
        print("("+tmp_db_name+")", end="")

        # step 2 execute DDL query 
        try:
            cur.execute(query)
            conn.commit()
            rows.append(cur.fetchall())
        except psycopg2.Error as errorMsg:  
            conn.rollback()

        # step 3 delete table 
        try:
            cur.execute(query_delete_temp_db)
            conn.commit()
        except psycopg2.Error as errorMsg:  
            conn.rollback()
        
        return rows
    except Exception as error:
        print("Database query error: ", error, question, end="")
        print("Exception TYPE:", type(error), question, end="")

def summarize_sql_output(rows):
    if rows is None or len(rows) < 1:
        return "No output"
    output_summary = str(len(rows[0])) + ", " 
    if len(rows[0]) > 1:
        # We only keep the first 10 rows in per output
        output_summary = output_summary + str(rows[0][:10])
    else:
        output_summary = output_summary + str(rows[0])
    return output_summary


def validate_sql_output(query_output_rows, num_rows, rows_checklist=[], sorted=False):
    comment = ''
    # Step 1: check the number of rows
    if num_rows != len(query_output_rows):
        comment += "Wrong number of rows (" + num_rows +" expected, but " + len(query_output_rows) + "obeserved).\n"
    
    # Step 2: spot-check/audit over the rows
    all_right = 1
    example_missing_row = ""
    for item in rows_checklist:
        if item not in query_output_rows:
            all_right *= 0
            example_missing_row = item
    if all_right != 1:
        comment += "Rows missing from the output (e.g.," + item + ").\n"

    # Step 3: check if the order of rows are correct (optional)
    if sorted:
        all_right = 1
        for index, item in enumerate(rows_checklist):
            if query_output_rows[index] != item:
                all_right *= 0
        if all_right != 1:
            comment += "Inconsistent of output (wrong order).\n"
    
    return comment

def check_illegal_character(solution, comment=''):
    if len(comment) > 0:
            comment += '\n' 
    illegal_chars = ['\uff0c', '\uff08', '\u201d', '\u201c', '\uff0c', '\u2018', '\u2019'] 
    illegal_chars_plaintext = ['ff0c', 'ff08', '201d', '201c', 'ff0c', '2018', '2019'] 
    check = []
    for idx, char in enumerate(illegal_chars):
        if char in solution:
            check.append(illegal_chars_plaintext[idx])
    
    if len(check) > 0:
        comment += 'Illegal fullwidth character detected ' + str(check) + '; '
    return comment 

def check_semicolons(solution, question_index, comment=''):
    # For the last two questions, we donot need to check
    if question_index >= 6:
        return comment
    if len(solution) > 0 and solution.find(';') < 0:
        if len(comment) > 0:
            comment += '\n' 
        comment += 'Missing semicolon, CHECK CODE; '  
    return comment

def check_multiple_queries(solution, question_index, comment=''):
    # For the last two questions, we donot need to check
    if question_index >= 6:
        return comment
    if solution.count(';') > 1:
        if len(comment) > 0:
            comment += '\n' 
        comment += 'Multiple semicolons detected, CHECK CODE; '  
    return comment

def check_usage_of_aggregation(solution, question_index, comment=''):

    if question_index < 3 or question_index > 4:
        return comment
    clue_str = []
    if re.search('count ', solution, re.IGNORECASE):
        clue_str.append('COUNT')
    if re.search('having', solution, re.IGNORECASE):
        clue_str.append('HAVING')
    if re.search('group by', solution, re.IGNORECASE):
        clue_str.append('GROUP-BY')
    
    if len(clue_str) > 0:
        if len(comment) > 0:
            comment += '\n' 
        comment = 'Aggregation ' + str(clue_str)+ ' is used, CHECK CODE; '  
    return comment

def check_missing_of_aggregation(solution, question_index, comment=''):

    if question_index != 2:
        return comment
    if not re.search('having', solution, re.IGNORECASE):
        if not re.search('group by', solution, re.IGNORECASE):
            if len(comment) > 0:
                comment += '\n' 
            comment += 'Aggregation is missing, CHECK CODE; '
    return comment

def check_ddl_correctness(solution, question_index, comment=''):
    if question_index != 6:
        return comment
    else:
        solution_strip_str = solution.strip().replace('\n', ' ').replace('\t', '').replace(' ', '').lower()
        num_tables = solution_strip_str.count('create table'.replace(' ', ''))
        num_not_null = solution_strip_str.count('not null'.replace(' ', ''))
        num_fkey = solution_strip_str.count('references'.replace(' ', ''))

        if len(comment) > 0:
            comment += '\n' 
        comment += "Num. tables: " + str(num_tables) + "; "

        '''
        not_null_constraint_check = "Num. not null: " + str(num_not_null)
        if num_not_null < 4:
            not_null_constraint_check += " (CHECK CODE) "
        comment += not_null_constraint_check + "; "

        forigen_key_check = "Num. foreign keys defined: " + str(num_fkey)
        if num_fkey > 0:
            forigen_key_check += " (CHECK CODE) "
        comment += forigen_key_check + "; "
        '''
        
        return comment


def check_solution_format(solution, question_index, comment=''):
    
    if question_index == 5: # Question 1.f
        solution_strip_str = solution.strip().replace('\n', ' ').replace('\t', '').replace(' ', '').lower()
        check = []
        if 'rank'.replace(' ', '') in solution_strip_str:
            check.append("RANK")
        
        if 'row_number'.replace(' ', '') in solution_strip_str:
            check.append("ROW_NUMBER")
        
        if len(check) > 0:
            comment += "Answer violates requirement " + str(check) + ", CHECK CODE;"
            
    return comment


def perform_extra_checking(solution, question_index, comment=''):
    if comment is None:
        comment = ''
    comment = check_illegal_character(solution, comment)
    comment = check_semicolons(solution, question_index, comment)
    comment = check_multiple_queries(solution, question_index, comment)
    comment = check_usage_of_aggregation(solution, question_index,comment)
    comment = check_missing_of_aggregation(solution, question_index,comment)
    comment = check_solution_format(solution, question_index, comment)
    comment = check_ddl_correctness(solution, question_index, comment)
    
    return comment
    
dirpath=('submission\\test1\\')
arr = retrieve_all_submission_files(dirpath)

questions = ['1.a',  '1.b', '1.c',  '1.d', '1.e', '1.f', '2.a', '2.b']
extract_student_answers(arr, 
    project_questions = questions, 
    csv_format = ['comment', 'grade'], 
    output_file = 'test1.csv')