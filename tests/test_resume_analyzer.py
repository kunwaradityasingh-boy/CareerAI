import pytest
from backend.services.resume_analyzer_service import (
    analyze_resume_content,
    ROLE_SKILL_MAP,
)


def test_resume_analysis_full_stack():
    sample_resume = """
    John Doe
    john.doe@example.com | (555) 123-4567 | linkedin.com/in/johndoe | github.com/johndoe

    Professional Summary
    Experienced Full Stack Developer with 3+ years of experience building modern web applications.

    Technical Skills
    Languages & Frameworks: JavaScript, TypeScript, React, Node.js, Python, FastAPI, SQL, PostgreSQL, HTML, CSS.
    Tools & Platforms: Docker, Git, AWS, CI/CD, Redis, Tailwind CSS.

    Experience
    Senior Software Engineer | Tech Corp (2022 - Present)
    - Architected and deployed microservices backend using FastAPI and PostgreSQL, serving 50,000+ active users.
    - Optimized SQL queries and Redis caching, reducing API latency by 45%.
    - Spearheaded migration of legacy frontend to React and TypeScript with Tailwind CSS.
    - Collaborated with cross-functional teams in Agile sprints and maintained 90% test coverage with Jest.

    Projects
    Career Intelligence Platform
    - Engineered full-stack web portal using React, Node.js, and Docker.
    - Integrated REST APIs with automated CI/CD pipeline on AWS, improving deployment speed by 60%.

    Education
    Bachelor of Technology in Computer Science (2018 - 2022)
    State University
    """

    result = analyze_resume_content(sample_resume, target_role="Full Stack Developer")

    assert result["overall_score"] >= 70
    assert result["ats_compatibility"] >= 80
    assert result["skills_score"] >= 70
    assert "React" in result["found_keywords"]
    assert "FastAPI" in result["found_keywords"]
    assert "PostgreSQL" in result["found_keywords"]
    assert len(result["strengths"]) > 0
    assert "Experience / Projects" in result["sections_detected"]
    assert result["sections_detected"]["Experience / Projects"] is True


def test_resume_analysis_empty_or_too_short():
    with pytest.raises(ValueError, match="too short"):
        analyze_resume_content("Too short", target_role="Frontend Developer")


def test_resume_analysis_identifies_missing_keywords():
    basic_resume = """
    Jane Smith
    jane@example.com | 123-456-7890
    Summary: Beginner developer looking for junior roles.
    Education: B.S. in Computer Science.
    Skills: HTML, CSS, JavaScript.
    Projects: Built a simple calculator website.
    """

    result = analyze_resume_content(basic_resume, target_role="Full Stack Developer")
    assert result["overall_score"] < 70
    assert len(result["missing_keywords"]) > 0
    assert any("TypeScript" in k or "Docker" in k or "React" in k for k in result["missing_keywords"])
