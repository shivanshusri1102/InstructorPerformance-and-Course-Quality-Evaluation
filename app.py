"""
EduPro Online Platform — Instructor & Course Quality Analytics Dashboard
Run with: streamlit run app.py
Requires EduPro_Online_Platform.xlsx in the same folder (Teachers, Courses, Transactions sheets).
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="EduPro Instructor & Course Analytics", layout="wide", page_icon="🎓")

# ---------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------
@st.cache_data
def load_data(path="EduPro_Online_Platform.xlsx"):
    teachers = pd.read_excel(path, sheet_name="Teachers")
    courses = pd.read_excel(path, sheet_name="Courses")
    trans = pd.read_excel(path, sheet_name="Transactions")

    # one teacher per course (most recent / first observed mapping)
    course_teacher = trans[["CourseID", "TeacherID"]].drop_duplicates(subset="CourseID")
    courses_full = courses.merge(course_teacher, on="CourseID", how="left").merge(
        teachers, on="TeacherID", how="left"
    )

    enroll = trans.groupby("TeacherID").size().rename("Enrollments")
    teachers_full = teachers.merge(enroll, on="TeacherID", how="left").fillna({"Enrollments": 0})
    teachers_full["RatingTier"] = pd.cut(
        teachers_full["TeacherRating"], bins=[0, 2.5, 3.5, 5], labels=["Low (≤2.5)", "Mid (2.5–3.5)", "High (>3.5)"]
    )
    return teachers, courses, trans, courses_full, teachers_full


try:
    teachers, courses, trans, courses_full, teachers_full = load_data()
except FileNotFoundError:
    st.error(
        "Could not find **EduPro_Online_Platform.xlsx**. Place it in the same folder as app.py "
        "(it must contain Teachers, Courses and Transactions sheets), then refresh."
    )
    st.stop()

# ---------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------
st.sidebar.header("🔎 Filters")

expertise_opts = sorted(teachers_full["Expertise"].dropna().unique())
sel_expertise = st.sidebar.multiselect("Instructor expertise", expertise_opts, default=expertise_opts)

category_opts = sorted(courses_full["CourseCategory"].dropna().unique())
sel_category = st.sidebar.multiselect("Course category", category_opts, default=category_opts)

level_opts = sorted(courses_full["CourseLevel"].dropna().unique())
sel_level = st.sidebar.multiselect("Course level", level_opts, default=level_opts)

rating_range = st.sidebar.slider("Teacher rating range", 1.0, 5.0, (1.0, 5.0), step=0.1)
exp_range = st.sidebar.slider(
    "Years of experience",
    int(teachers_full["YearsOfExperience"].min()),
    int(teachers_full["YearsOfExperience"].max()),
    (int(teachers_full["YearsOfExperience"].min()), int(teachers_full["YearsOfExperience"].max())),
)

# filtered frames
f_teachers = teachers_full[
    teachers_full["Expertise"].isin(sel_expertise)
    & teachers_full["TeacherRating"].between(*rating_range)
    & teachers_full["YearsOfExperience"].between(*exp_range)
]

f_courses = courses_full[
    courses_full["CourseCategory"].isin(sel_category)
    & courses_full["CourseLevel"].isin(sel_level)
    & courses_full["Expertise"].isin(sel_expertise)
]

# ---------------------------------------------------------------
# Header & KPIs
# ---------------------------------------------------------------
st.title("🎓 EduPro — Instructor & Course Quality Analytics")
st.caption("A data-driven framework to evaluate teaching effectiveness and course quality consistency.")

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Average Teacher Rating", f"{f_teachers['TeacherRating'].mean():.2f}")
k2.metric("Average Course Rating", f"{f_courses['CourseRating'].mean():.2f}")
k3.metric(
    "Rating Consistency Index",
    f"{1 - (f_teachers['TeacherRating'].std() / f_teachers['TeacherRating'].mean()):.2f}",
    help="1 − (StdDev / Mean) of Teacher Rating. Closer to 1 = more consistent quality across instructors.",
)
exp_corr = f_teachers["YearsOfExperience"].corr(f_teachers["TeacherRating"])
k4.metric("Experience Impact Score", f"{exp_corr:.2f}", help="Correlation between YearsOfExperience and TeacherRating.")
k5.metric("Active Instructors", f"{f_teachers.shape[0]}")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(
    ["🏆 Instructor Leaderboard", "📈 Experience vs Rating", "🗂️ Course Quality Heatmap", "🧩 Expertise Comparison"]
)

# ---------------------------------------------------------------
# Tab 1 — Leaderboard
# ---------------------------------------------------------------
with tab1:
    st.subheader("Instructor Performance Leaderboard")
    lb = f_teachers.sort_values("TeacherRating", ascending=False)[
        ["TeacherName", "Expertise", "YearsOfExperience", "TeacherRating", "Enrollments"]
    ].reset_index(drop=True)
    lb.index += 1
    st.dataframe(lb, use_container_width=True, height=420)

    c1, c2 = st.columns(2)
    with c1:
        top10 = lb.head(10)
        fig = px.bar(top10, x="TeacherRating", y="TeacherName", orientation="h", color="TeacherRating",
                     color_continuous_scale="Blues", title="Top 10 Instructors")
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        bottom10 = lb.tail(10).sort_values("TeacherRating")
        fig2 = px.bar(bottom10, x="TeacherRating", y="TeacherName", orientation="h", color="TeacherRating",
                      color_continuous_scale="Reds_r", title="Bottom 10 Instructors")
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Enrollment Influence by Rating Tier")
    tier_summary = f_teachers.groupby("RatingTier", observed=True).agg(
        AvgEnrollments=("Enrollments", "mean"), Instructors=("TeacherID", "count")
    ).reset_index()
    fig3 = px.bar(tier_summary, x="RatingTier", y="AvgEnrollments", color="RatingTier",
                  text="Instructors", title="Average Enrollments per Instructor by Rating Tier")
    st.plotly_chart(fig3, use_container_width=True)

# ---------------------------------------------------------------
# Tab 2 — Experience vs Rating
# ---------------------------------------------------------------
with tab2:
    st.subheader("Years of Experience vs Teacher Rating")
    fig = px.scatter(
        f_teachers, x="YearsOfExperience", y="TeacherRating", color="Expertise", size="Enrollments",
        hover_data=["TeacherName"], trendline="ols", title=f"Correlation = {exp_corr:.2f}"
    )
    st.plotly_chart(fig, use_container_width=True)

    f_teachers_b = f_teachers.copy()
    f_teachers_b["ExpBucket"] = pd.cut(
        f_teachers_b["YearsOfExperience"], bins=[0, 3, 7, 12, 25], labels=["0–3 yrs", "4–7 yrs", "8–12 yrs", "13+ yrs"]
    )
    bucket_avg = f_teachers_b.groupby("ExpBucket", observed=True)["TeacherRating"].mean().reset_index()
    fig2 = px.line(bucket_avg, x="ExpBucket", y="TeacherRating", markers=True,
                   title="Average Rating by Experience Bucket (diminishing-returns check)")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Teacher Rating vs Course Rating")
    fig3 = px.scatter(f_courses, x="TeacherRating", y="CourseRating", color="CourseCategory",
                      trendline="ols", title=f"Correlation = {f_courses['TeacherRating'].corr(f_courses['CourseRating']):.2f}")
    st.plotly_chart(fig3, use_container_width=True)

# ---------------------------------------------------------------
# Tab 3 — Course Quality Heatmap
# ---------------------------------------------------------------
with tab3:
    st.subheader("Course Rating Heatmap: Category × Level")
    pivot = f_courses.pivot_table(values="CourseRating", index="CourseCategory", columns="CourseLevel", aggfunc="mean")
    fig = px.imshow(pivot, text_auto=".2f", color_continuous_scale="RdYlGn", aspect="auto",
                    title="Average Course Rating by Category and Level")
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        cat_avg = f_courses.groupby("CourseCategory")["CourseRating"].mean().sort_values(ascending=False).reset_index()
        fig2 = px.bar(cat_avg, x="CourseRating", y="CourseCategory", orientation="h", color="CourseRating",
                      color_continuous_scale="Viridis", title="Average Rating by Course Category")
        st.plotly_chart(fig2, use_container_width=True)
    with c2:
        gender_level = f_courses.groupby(["Gender", "CourseLevel"])["CourseRating"].mean().reset_index()
        fig3 = px.bar(gender_level, x="CourseLevel", y="CourseRating", color="Gender", barmode="group",
                      title="Gender vs Course Level Rating Comparison")
        st.plotly_chart(fig3, use_container_width=True)

# ---------------------------------------------------------------
# Tab 4 — Expertise Comparison
# ---------------------------------------------------------------
with tab4:
    st.subheader("Expertise-wise Performance Comparison")
    exp_summary = f_courses.groupby("Expertise").agg(
        AvgCourseRating=("CourseRating", "mean"),
        AvgTeacherRating=("TeacherRating", "mean"),
        Courses=("CourseID", "nunique"),
    ).reset_index().sort_values("AvgCourseRating", ascending=False)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=exp_summary["Expertise"], y=exp_summary["AvgCourseRating"], name="Avg Course Rating"))
    fig.add_trace(go.Scatter(x=exp_summary["Expertise"], y=exp_summary["AvgTeacherRating"], name="Avg Teacher Rating",
                             mode="lines+markers", yaxis="y"))
    fig.update_layout(title="Course Quality vs Teaching Quality by Expertise Area", barmode="group")
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(exp_summary, use_container_width=True)

    st.info(
        "**Reading this tab:** Expertise areas where Avg Course Rating closely tracks Avg Teacher Rating "
        "indicate teaching quality is the main driver of course success in that domain. Large gaps suggest "
        "other factors (content design, pricing, course length) play a bigger role."
    )

st.divider()
st.caption("EduPro Online Platform · Instructor & Course Quality Evaluation Framework · Built with Streamlit")
