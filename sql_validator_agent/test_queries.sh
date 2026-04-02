#!/bin/bash
# Sample commands to test the SQL Validator against the aiml_academic schema

echo "Testing Valid SELECT Query"
curl -X POST "http://localhost:8000/validate" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT student_name FROM aiml_academic.students;"}'
echo -e "\n---------------------------------------------\n"

echo "Testing Query with Data Range Criteria"
curl -X POST "http://localhost:8000/validate" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM aiml_academic.result_sessions WHERE study_year = 2 AND semester_no = 4;"}'
echo -e "\n---------------------------------------------\n"

echo "Testing Out of Bound Data Range (Expected: Rejected)"
curl -X POST "http://localhost:8000/validate" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM aiml_academic.result_sessions WHERE study_year = 5;"}'
echo -e "\n---------------------------------------------\n"

echo "Testing Stacked SQL Injection (Expected: Rejected)"
curl -X POST "http://localhost:8000/validate" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM aiml_academic.students; DROP TABLE aiml_academic.students;"}'
echo -e "\n---------------------------------------------\n"

echo "Testing DML/DDL Statement Bypass (Expected: Rejected)"
curl -X POST "http://localhost:8000/validate" \
  -H "Content-Type: application/json" \
  -d '{"query": "DELETE FROM aiml_academic.students;"}'
echo -e "\n---------------------------------------------\n"

