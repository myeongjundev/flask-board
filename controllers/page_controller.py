from flask import Blueprint, render_template

page_bp = Blueprint("page", __name__)


@page_bp.get("/")
def index():
    return render_template("index.html")


@page_bp.get("/dashboard")
def dashboard():
    return render_template("dashboard.html")
