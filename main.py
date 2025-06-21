from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Column, Integer, Float, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import math

# FastAPI app
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Database setup
DATABASE_URL = "sqlite:///./calculations.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ORM Model
class Calculation(Base):
    __tablename__ = "calculations"
    id = Column(Integer, primary_key=True, index=True)
    house_price = Column(Float)
    interest_rate = Column(Float)
    loan_term_years = Column(Integer)
    target_monthly_payment = Column(Float)
    current_savings = Column(Float)
    monthly_saving = Column(Float)
    down_payment = Column(Float)
    years_to_goal = Column(Integer)
    months_to_goal = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Create DB table
Base.metadata.create_all(bind=engine)


# Calculator Logic
class HomeSavingsPlanner:
    def __init__(self, house_price, interest_rate, loan_term_years,
                 target_monthly_payment, current_savings, monthly_saving):
        self.house_price = house_price
        self.annual_interest_rate = interest_rate
        self.loan_term_years = loan_term_years
        self.target_monthly_payment = target_monthly_payment
        self.current_savings = current_savings
        self.monthly_saving = monthly_saving

    def _max_loan_amount(self):
        r = self.annual_interest_rate / 12 / 100
        n = self.loan_term_years * 12
        M = self.target_monthly_payment
        numerator = M * ((1 + r) ** n - 1)
        denominator = r * (1 + r) ** n
        return numerator / denominator

    def _required_down_payment(self):
        loan_amount = self._max_loan_amount()
        return max(self.house_price - loan_amount, 0)

    def time_to_afford_home(self):
        down_payment_needed = self._required_down_payment()
        shortfall = down_payment_needed - self.current_savings
        if shortfall <= 0:
            return 0, 0, down_payment_needed
        months_needed = math.ceil(shortfall / self.monthly_saving)
        years = months_needed // 12
        months = months_needed % 12
        return years, months, down_payment_needed


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/calculate")
async def calculate(data: dict):
    try:
        planner = HomeSavingsPlanner(
            house_price=float(data["house_price"]),
            interest_rate=float(data["interest_rate"]),
            loan_term_years=int(data["loan_term_years"]),
            target_monthly_payment=float(data["target_monthly_payment"]),
            current_savings=float(data["current_savings"]),
            monthly_saving=float(data["monthly_saving"]),
        )
        years, months, down_payment = planner.time_to_afford_home()

        # Store in DB
        db = SessionLocal()
        record = Calculation(
            house_price=planner.house_price,
            interest_rate=planner.annual_interest_rate,
            loan_term_years=planner.loan_term_years,
            target_monthly_payment=planner.target_monthly_payment,
            current_savings=planner.current_savings,
            monthly_saving=planner.monthly_saving,
            down_payment=round(down_payment, 2),
            years_to_goal=years,
            months_to_goal=months,
        )
        db.add(record)
        db.commit()
        db.close()

        return JSONResponse({
            "years": years,
            "months": months,
            "down_payment": round(down_payment, 2)
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        reload=True,
        port=int("8000"),
    )