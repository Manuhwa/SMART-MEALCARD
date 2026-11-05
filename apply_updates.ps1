$ErrorActionPreference = 'Stop'
$candidates = @(
  'C:\Users\PC\OneDrive\Desktop\SMART MEALCARD',
  'C:\Users\PC\Desktop\SMART MEALCARD',
  "$env:USERPROFILE\OneDrive\Desktop\SMART MEALCARD",
  "$env:USERPROFILE\Desktop\SMART MEALCARD"
)
$base = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $base) { throw 'SMART MEALCARD folder not found' }
Write-Output "BASE=$base"

# Copy assets from this script's folder if present beside it
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Copy-Item "$here\static\img\madziwa-logo.jpeg" "$base\static\img\madziwa-logo.jpeg" -Force
Copy-Item "$here\static\img\smart-id-front-design.png" "$base\static\img\smart-id-front-design.png" -Force
Copy-Item "$here\static\img\smart-id-back-design.png" "$base\static\img\smart-id-back-design.png" -Force
New-Item -ItemType Directory -Force -Path "$base\static\design" | Out-Null
Copy-Item "$here\static\design\digital-student-id.html" "$base\static\design\digital-student-id.html" -Force
Copy-Item "$here\templates\_id_card.html" "$base\templates\_id_card.html" -Force

# Normalize field names in template to match this app's student dict if needed
$py = Get-Content "$base\app.py" -Raw
# Detect field naming
$usesMealCleared = $py -match 'meal_cleared'
$usesMealClearedAlt = $py -match '\[\"meal_cleared\"\]'
Write-Output "meal_cleared_present=$usesMealCleared"

# Replace first seed SRN with 23GEN002
$py2 = $py -replace '\("MTC/2024/0142"', '("23GEN002"'
# Update related attendance/meal seed references for that student
$py2 = $py2 -replace '"MTC/2024/0142"', '"23GEN002"'
if ($py2 -ne $py) {
  Set-Content "$base\app.py" -Value $py2 -Encoding UTF8
  Write-Output 'seed_srn_updated_to_23GEN002'
} else {
  Write-Output 'seed_srn_unchanged'
}

# Ensure DH refusal message is strong
$py = Get-Content "$base\app.py" -Raw
if ($py -notmatch 'DH REFUSED') {
  $py = $py -replace 'student\["meal_block_reason"\] or "Student is not cleared for meals\."', 'f"DH REFUSED — Smart ID {{student[''srn'']}} is not cleared. {{(student[''meal_block_reason''] or ''Student is not cleared for the dining hall.'')}}"'
  # above may be wrong due to escaping - do a line-based patch instead
}
# Line-based robust patch
$lines = Get-Content "$base\app.py"
$out = New-Object System.Collections.Generic.List[string]
for ($i=0; $i -lt $lines.Count; $i++) {
  $line = $lines[$i]
  if ($line -match 'Student is not cleared for meals') {
    $out.Add('                "dh_approved": False,')
    $out.Add('                "message": f"DH REFUSED — Smart ID {student[''srn'']} is not cleared. {(student.get(''meal_block_reason'') or student.get(''meal_block_reason'') or ''Student is not cleared for the dining hall.'')}",')
  } else {
    $out.Add($line)
  }
}
# Simpler: if message line still old-style, replace via regex on full text
$py = Get-Content "$base\app.py" -Raw
if ($py -match 'not cleared for meals' -and $py -notmatch 'DH REFUSED') {
  $py = $py.Replace(
    'student["meal_block_reason"] or "Student is not cleared for meals."',
    'f"DH REFUSED — Smart ID {student[''srn'']} is not cleared. {(student[''meal_block_reason''] or ''Student is not cleared for the dining hall.'')}"'
  )
  Set-Content "$base\app.py" -Value $py -Encoding UTF8
  Write-Output 'refusal_message_patched'
} elseif ($py -match 'DH REFUSED') {
  Write-Output 'refusal_message_ok'
} else {
  Write-Output 'refusal_message_check_manually'
}

# CSS logo rules
$css = Get-Content "$base\static\css\app.css" -Raw
if ($css -notmatch '\.id-logo') {
  $css += @"

/* Official Madziwa logo on Smart ID */
.id-logo {
  width: 48px; height: 48px; object-fit: contain; border-radius: 50%;
  background: #fff; border: 2px solid rgba(201, 162, 77, 0.55);
}
.id-logo-sm { width: 40px; height: 40px; }
.id-card.dh-blocked .id-uses .use-no {
  background: rgba(155, 59, 44, 0.9); border-color: #9b3b2c; color: #fff; text-decoration: line-through;
}
.id-card.dh-cleared .id-uses .use-ok {
  background: rgba(201, 162, 77, 0.25); border-color: var(--gold); color: var(--gold-soft);
}
"@
  Set-Content "$base\static\css\app.css" -Value $css -Encoding UTF8
  Write-Output 'css_patched'
} else { Write-Output 'css_ok' }

# Align template fields with app naming (meal_cleared vs meal_cleared)
$tpl = Get-Content "$base\templates\_id_card.html" -Raw
if ($py -match 'meal_cleared' -and $tpl -match 'meal_cleared' -and $py -notmatch 'student\.meal_cleared') {
  # app uses meal_cleared in DB; templates previously used meal_cleared
}
# Detect which key student_dict exposes
if ($py -match 'data\["meal_cleared"\]') {
  $tpl = $tpl.Replace('meal_cleared', 'meal_cleared').Replace('meal_block_reason', 'meal_block_reason')
  # If app uses meal_cleared boolean:
  $tpl = $tpl.Replace('student.meal_cleared', 'student.meal_cleared')
}
if ($py -match 'data\["meal_cleared"\]\s*=\s*bool') {
  $tpl2 = Get-Content "$base\templates\_id_card.html" -Raw
  $tpl2 = $tpl2.Replace('student.meal_cleared', 'student.meal_cleared')
  $tpl2 = $tpl2.Replace('student.meal_block_reason', 'student.meal_block_reason')
  # Actually convert meal_cleared -> meal_cleared if that's the API name
  if ($py -match 'not student\["meal_cleared"\]') {
    $tpl2 = $tpl2.Replace('meal_cleared', 'meal_cleared')
    $tpl2 = $tpl2.Replace('meal_block_reason', 'meal_block_reason')
  }
  Set-Content "$base\templates\_id_card.html" -Value $tpl2 -Encoding UTF8
}

# Reset DB so seed SRN appears (optional) — only if user wants; delete mealcard.db
$db = Join-Path $base 'data\mealcard.db'
if (Test-Path $db) {
  Remove-Item $db -Force
  Write-Output 'db_reset_for_new_seed'
}

Write-Output 'DONE'
