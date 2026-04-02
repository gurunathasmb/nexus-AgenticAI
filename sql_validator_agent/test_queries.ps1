Write-Host "Testing Valid SELECT Query"
Invoke-RestMethod -Uri "http://localhost:8000/validate" -Method Post -ContentType "application/json" -Body '{"query": "SELECT student_name FROM aiml_academic.students;"}'
Write-Host "`n---------------------------------------------`n"

Write-Host "Testing Query with Data Range Criteria"
Invoke-RestMethod -Uri "http://localhost:8000/validate" -Method Post -ContentType "application/json" -Body '{"query": "SELECT * FROM aiml_academic.result_sessions WHERE study_year = 2 AND semester_no = 4;"}'
Write-Host "`n---------------------------------------------`n"

Write-Host "Testing Out of Bound Data Range (Expected: 400 Bad Request)"
Try {
    Invoke-RestMethod -Uri "http://localhost:8000/validate" -Method Post -ContentType "application/json" -Body '{"query": "SELECT * FROM aiml_academic.result_sessions WHERE study_year = 5;"}'
} Catch {
    Write-Host "Rejected as expected: $($_.Exception.Message)"
}
Write-Host "`n---------------------------------------------`n"

Write-Host "Testing Stacked SQL Injection (Expected: 400 Bad Request)"
Try {
    Invoke-RestMethod -Uri "http://localhost:8000/validate" -Method Post -ContentType "application/json" -Body '{"query": "SELECT * FROM aiml_academic.students; DROP TABLE aiml_academic.students;"}'
} Catch {
    Write-Host "Rejected as expected: $($_.Exception.Message)"
}
Write-Host "`n---------------------------------------------`n"

Write-Host "Testing DML/DDL Statement Bypass (Expected: 400 Bad Request)"
Try {
    Invoke-RestMethod -Uri "http://localhost:8000/validate" -Method Post -ContentType "application/json" -Body '{"query": "DELETE FROM aiml_academic.students;"}'
} Catch {
    Write-Host "Rejected as expected: $($_.Exception.Message)"
}
Write-Host "`n---------------------------------------------`n"
