# Production Deployment & DevOps Guide

## Dhanekula Institute of Engineering and Technology (DIET)
### Academic Planning & Management Platform

---

## 1. Local Development Setup

```bash
# 1. Clone repository and navigate
cd c:/Users/Admin/Desktop/E_Planner

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize database with seed data
python scripts/seed_data.py

# 4. Run development server
python run.py
```
Access at `http://localhost:5000`

---

## 2. Docker & Containerized Deployment

```bash
# Build and start web server and PostgreSQL database
docker-compose up -d --build

# Run database migrations / seed
docker-compose exec web python scripts/seed_data.py

# Check status
docker-compose ps
```
Access at `http://localhost:8000`

---

## 3. Production Environment Checklist

- [x] Set strong `SECRET_KEY` in `.env`
- [x] Configure PostgreSQL `DATABASE_URL`
- [x] Ensure `DEBUG = False`
- [x] Enable HTTPS and secure cookie flags
- [x] Configure automated database backups
- [x] Set file upload size limits (16MB default)
- [x] Verify Gunicorn multi-worker configuration
