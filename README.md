# Madziwa Teachers College Smart Student ID

A college desk for **Madziwa Teachers College, Shamva**. One Smart ID card holds the student SRN and personal particulars, marks lecture attendance, and works as a meal card.

## What the Smart ID does

- **Identity card** — SRN, photo, programme, national ID, hostel, next of kin, and a QR code
- **Attendance** — lecturers scan the card or mark a class roll
- **Meal card** — dining hall scans the same card
  - **Not cleared** students are refused (fees or discipline)
  - A student may collect **one portion per meal** (breakfast, lunch, dinner)

## Run it

```bash
python -m pip install -r requirements.txt
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

Demo accounts are created on first launch:

| Desk | Username | Password |
| --- | --- | --- |
| Registry | `admin` | `admin123` |
| Lecturer | `lecturer` | `lecturer123` |
| Dining hall | `kitchen` | `kitchen123` |
| Student (cleared) | `MTC/2024/0142` | `student123` |
| Student (not cleared) | `MTC/2025/0087` | `student123` |

Records are stored in `data/mealcard.db`. Delete that file to reseedsample students.
