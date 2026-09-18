# Madziwa Teachers College Smart Student ID

A college desk for **Madziwa Teachers College, Shamva**. One Smart ID card holds the student SRN and personal particulars, marks lecture attendance, and works as a meal card.

## What the Smart ID does

The Smart ID QR code (format: `MTC|{SRN}`) is the **single scan key** for both attendance and dining hall:

- **Identity card** — SRN, photo, programme, national ID, hostel, next of kin, and a QR code
- **Attendance desk** (`/attendance`) — lecturers scan the QR or type the SRN to mark students **present** for the selected date/session/course. The same card used at the dining hall marks presence in class.
- **Dining hall desk** (`/meals`) — kitchen staff scan the same QR to serve meals with strict rules:
  - **One meal per period per day** — a student may collect at most one portion per meal period (breakfast, lunch, supper) per calendar day
  - **Second scan refused** — scanning the same ID again for the same meal period on the same day is rejected with an `already_served` result showing the time of first serve
  - **Not cleared students refused** — students with `meal_cleared = false` cannot get meals (for outstanding fees or discipline); the block reason is displayed
  - **Race-safe** — concurrent double-tap is handled safely via database UNIQUE constraint

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
