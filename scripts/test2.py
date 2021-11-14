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

dbname='exam'
user='postgres'
password='admin'
host='localhost'

drop_all_temp_views = "SELECT 'DROP VIEW IF EXISTS ' || table_name || ';' "\
    "FROM information_schema.views WHERE table_schema"\
        " NOT IN ('pg_catalog', 'information_schema') AND table_name !~ '^pg_';"

SPECIAL_PARAMS_Q1 = [' LIMIT 3 OFFSET 37;', ' LIMIT 3 offset 3756;']

CORRECT_OUTPUT_LEN = 5335
SLIGHTLY_WRONG_OUTPUT_LEN = 5336


initialize_connection_command = "dbname='" + dbname + "' user='" + user + "' host='" + host + "' password='" + password + "'" 
initialize_connection_command_no_db = "user='" + user + "' host='" + host + "' password='" + password + "'" 

EXECUTE_QUERY = True
KEEP_LINE_BREAK = True

regex = re.compile(r'[\n\r\t]')

default_question_pattern = '/* Question '
default_header_line_number = 6

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
            sid = file_name.split('.txt')[0]
        sid_list.append(sid)
        file_list.append(filepath)
    
    return sid_list, file_list


# Retrieve all files for a specific project
def retrieve_all_submission_files(dirpath):
    files = os.listdir(dirpath)
    files_with_path = []
    for filename in files:
        if filename[-4:] == '.txt':
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
    
    for qn in project_questions:
        header.append(qn)
        if EXECUTE_QUERY and qn == '1.a':
            header.append('output')
            for param in SPECIAL_PARAMS_Q1:
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
        output_comment = ''
        within_comment_block = False
    

        # Strips the newline character
        for line in reader_lines:
            line_count += 1

            if match_pattern:
                # increment question counting and reset match pattern
                match_pattern = False
                if question_index >= 0:
                    student_row.append(solution_string.strip())

                    extra_comment = perform_extra_checking(solution_string, question_index, extra_comment)

                    if EXECUTE_QUERY and question_index == 0:
                        # rows = psql_execute_query(solution_string.replace('\n', ' '), question="("+project_questions[question_index]+")")
                        rows = psql_execute_query(solution_string, question="("+project_questions[question_index]+")", question_index=question_index)
                        student_row.append(summarize_sql_output(rows)) 
                        
                        if rows is None or len(rows) < 1:
                            output_comment = 'No output;'
                        else:
                            if len(rows[0]) == CORRECT_OUTPUT_LEN:
                                output_comment = 'Correct output; '
                            elif len(rows[0]) == SLIGHTLY_WRONG_OUTPUT_LEN:
                                output_comment = 'Tiny mistake in output row number;'
                            else:
                                output_comment = 'Wrong output;'

                        # We perform a special arrangement for the test 1 as for Q1(f) we are generating
                        #  four variants and run them for outputs separately. 
                        # [2/2] Generate variants of query, execute them and record outputs
                        
                        if question_index == 0 and len(SPECIAL_PARAMS_Q1) > 0:
                            
                            print('(', end = "")
                            for param in SPECIAL_PARAMS_Q1:
                                if solution_string.strip().endswith(';'):
                                    solution_string_variant = solution_string.strip()[:-1] + str(param)
                                else:
                                    solution_string_variant = solution_string.strip() + str(param)
                                # solution_string_variant = solution_string.replace(str(ORIGINAL_PARAM_Q1F), str(param))
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
                    #for col in csv_format:
                    student_row.append(output_comment) 
                    student_row.append(extra_comment) 
                    student_row.append("")
                    extra_comment = ""
                    
                    output_comment = ''
                    extra_comment = ''
                    solution_string = ''
                print('.', end = "")
                question_index += 1
                logging.debug("SOLUTION OF " + project_questions[question_index] + " IS SHOWN BELOW:")

            if line.startswith(question_pattern):
                # Start reading the solution for the next question
                match_pattern = True
            elif line_count > 6:
                # Continue reading the solution for the current question if the question_index is not -1
                if len(line.strip()) > 0 and question_index == 0:
                    
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

                elif question_index != 0:
                    line = line.replace('/*','').replace('*/','')
                    if KEEP_LINE_BREAK:
                        if len(line.strip()) == 0:
                            line = ""
                    else:
                        line = line.strip()
                    logging.info("Line{}: {}".format(line_count, line.strip().encode('utf-8')))

                    if not line.find('Write your answer') > 0 and not line.find('Provided for your convenience') > 0 and\
                        not line.find('Edit the text in parenthesis') > 0 and not line.startswith('******'):
                        solution_string += line
                    
                    

        student_row.append(solution_string.strip())
        
        extra_comment = perform_extra_checking(solution_string, question_index,extra_comment)
        
        if EXECUTE_QUERY and question_index == 0:
        # while False: # leave the last question not been executed
            rows = psql_execute_query(solution_string, question="("+project_questions[question_index]+")", question_index=question_index)
            student_row.append(summarize_sql_output(rows)) 
        
        #for col in csv_format:
        student_row.append("") 
        student_row.append(extra_comment) 
        student_row.append("")
        extra_comment = ""
        
        writer.writerow(student_row)
        
        print('.')
        file_count += 1
    output_file.close()

def psql_execute_query(query, question="", question_index=0, time_out='10000'):
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
    if question_index >= 1:
        return comment
    if len(solution) > 0 and solution.find(';') < 0:
        if len(comment) > 0:
            comment += '\n' 
        comment += 'Missing semicolon; '  
    return comment

def check_multiple_queries(solution, question_index, comment=''):
    # For the last two questions, we donot need to check
    if question_index >= 1:
        return comment
    if solution.count(';') > 1:
        if len(comment) > 0:
            comment += '\n' 
        comment += 'Multiple semicolons detected; '  
    return comment

def check_usage_of_keywords(solution, question_index, comment=''):

    if question_index >= 1:
        return comment
    
    clue_str_to_have = ['COALESCE', 'ROLLUP']
    if re.search('coalesce', solution, re.IGNORECASE):
        clue_str_to_have.remove('COALESCE')
    if re.search('rollup', solution, re.IGNORECASE):
        clue_str_to_have.remove('ROLLUP')
    
    if len(clue_str_to_have) > 0:
        if len(comment) > 0:
            comment += '\n' 
        if 'COALESCE' in clue_str_to_have:
            comment += 'Missing COALESCE; '
        if 'ROLLUP' in clue_str_to_have:
            comment += 'Missing ROLLUP; '

    clue_str = []
    if re.search('with ', solution, re.IGNORECASE):
        clue_str.append('Usage of WITH detected; ')
    if re.search('view ', solution, re.IGNORECASE):
        clue_str.append('Usage of VIEW detected; ')
    

    return comment

def perform_extra_checking(solution, question_index, comment=''):
    if comment is None:
        comment = ''
    comment = check_illegal_character(solution, comment)
    comment = check_semicolons(solution, question_index, comment)
    comment = check_multiple_queries(solution, question_index, comment)
    comment = check_usage_of_keywords(solution, question_index,comment)
    
    return comment
    
dirpath=('submission\\test2\\')
arr = retrieve_all_submission_files(dirpath)

questions = ['1.a',  '2.a', '2.b', '2.c',  '3.a', '3.b', '4.a', '4.b', '4.c', '4.d']
extract_student_answers(arr, 
    project_questions = questions, 
    csv_format = ['comment_output', 'comment_answer', 'grade'], 
    output_file = 'test2.csv')