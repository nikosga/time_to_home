from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import math

app = FastAPI()
templates = Jinja2Templates(directory="templates")


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
            return (0, 0)
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