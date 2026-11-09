import io
import re
from typing import Any, Dict, List, Optional
import pypdf

# Comprehensive Skill Ontologies by Role
ROLE_SKILL_MAP: Dict[str, Dict[str, List[str]]] = {
    "Full Stack Developer": {
        "core": ["JavaScript", "TypeScript", "React", "Node.js", "Python", "SQL", "HTML", "CSS", "Git", "REST API"],
        "advanced": ["Docker", "PostgreSQL", "MongoDB", "FastAPI", "Express", "Next.js", "Tailwind CSS", "Redis", "CI/CD", "AWS"],
        "soft_impact": ["Agile", "System Design", "Code Review", "Unit Testing", "Debugging", "API Integration"],
    },
    "Frontend Developer": {
        "core": ["JavaScript", "TypeScript", "React", "HTML5", "CSS3", "Tailwind CSS", "Git", "REST API", "Responsive Design"],
        "advanced": ["Next.js", "Redux", "Vue.js", "Webpack", "Vite", "Jest", "GraphQL", "WebSockets", "Accessibility", "Performance Optimization"],
        "soft_impact": ["UI/UX", "Component Design", "Cross-browser Testing", "Prototyping", "Design Systems"],
    },
    "Backend Developer": {
        "core": ["Python", "Java", "Node.js", "SQL", "PostgreSQL", "FastAPI", "Django", "Git", "REST API", "Database Design"],
        "advanced": ["Docker", "Kubernetes", "Redis", "Kafka", "Microservices", "AWS", "gRPC", "GraphQL", "CI/CD", "Linux"],
        "soft_impact": ["Scalability", "System Architecture", "Security", "Query Optimization", "Unit Testing"],
    },
    "Data Scientist / AI Engineer": {
        "core": ["Python", "SQL", "Pandas", "NumPy", "Scikit-Learn", "Machine Learning", "Git", "Data Analysis", "Statistics"],
        "advanced": ["PyTorch", "TensorFlow", "Deep Learning", "NLP", "LLMs", "Computer Vision", "Docker", "MLOps", "Hugging Face", "BigQuery"],
        "soft_impact": ["A/B Testing", "Feature Engineering", "Data Pipeline", "Model Evaluation", "Visualization"],
    },
    "DevOps / Cloud Engineer": {
        "core": ["Linux", "Git", "Docker", "Kubernetes", "CI/CD", "AWS", "Bash", "Networking", "Python"],
        "advanced": ["Terraform", "Ansible", "Prometheus", "Grafana", "Jenkins", "GitHub Actions", "GCP", "Azure", "Security", "Helm"],
        "soft_impact": ["Automation", "Infrastructure as Code", "Incident Management", "Monitoring", "Disaster Recovery"],
    },
    "Mobile App Developer": {
        "core": ["Flutter", "Dart", "React Native", "JavaScript", "Mobile UI", "REST API", "Git", "State Management"],
        "advanced": ["Kotlin", "Swift", "iOS", "Android", "Firebase", "SQLite", "GraphQL", "Push Notifications", "App Store Deployment"],
        "soft_impact": ["Offline Storage", "Performance Tuning", "Responsive Layouts", "Mobile Security"],
    },
    "Cyber Security Analyst": {
        "core": ["Networking", "Linux", "Python", "OWASP", "Vulnerability Assessment", "Firewalls", "Cryptography", "Git"],
        "advanced": ["Penetration Testing", "SIEM", "Wireshark", "Burp Suite", "Incident Response", "Identity Management", "Cloud Security", "Compliance"],
        "soft_impact": ["Risk Assessment", "Security Auditing", "Threat Modeling", "Policy Enforcement"],
    },
}

DEFAULT_SKILLS = {
    "core": ["Problem Solving", "Git", "Data Structures", "Algorithms", "SQL", "Object-Oriented Programming", "REST APIs"],
    "advanced": ["Docker", "Cloud", "CI/CD", "Linux", "Unit Testing", "Database Management", "System Architecture"],
    "soft_impact": ["Team Collaboration", "Agile", "Documentation", "Communication", "Troubleshooting"],
}

STRONG_ACTION_VERBS = [
    "accelerated", "achieved", "analyzed", "architected", "automated", "built",
    "coached", "collaborated", "constructed", "created", "decreased", "delivered",
    "deployed", "designed", "developed", "diagnosed", "engineered", "enhanced",
    "established", "executed", "formulated", "generated", "implemented", "improved",
    "increased", "initiated", "integrated", "launched", "led", "managed",
    "maximized", "mentored", "migrated", "minimized", "modeled", "modernized",
    "optimized", "orchestrated", "overhauled", "pioneered", "produced", "published",
    "reduced", "refactored", "resolved", "revamped", "scaled", "simplified",
    "spearheaded", "standardized", "streamlined", "strengthened", "transformed", "upgraded",
]

WEAK_PHRASES = [
    "responsible for", "duties included", "worked on", "helped with",
    "assisted in", "participated in", "attempted to", "handled daily",
]


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract readable text from PDF bytes."""
    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages_text = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                pages_text.append(extracted)
        return "\n".join(pages_text).strip()
    except Exception as exc:
        raise ValueError(f"Unable to parse PDF file: {exc}") from exc


def analyze_resume_content(
    resume_text: str,
    target_role: str,
    job_description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Performs comprehensive ATS scoring, keyword matching, impact analysis,
    and structured recommendations.
    """
    if not resume_text or len(resume_text.strip()) < 50:
        raise ValueError("Resume content is too short or empty for analysis.")

    cleaned_text = resume_text.strip()
    lower_text = cleaned_text.lower()

    # 1. Target Role & Skill Matching
    role_config = ROLE_SKILL_MAP.get(target_role, DEFAULT_SKILLS)
    all_role_skills = role_config["core"] + role_config["advanced"] + role_config["soft_impact"]

    found_skills: List[str] = []
    missing_skills: List[str] = []

    for skill in all_role_skills:
        # Check using word boundary or phrase match
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, lower_text):
            found_skills.append(skill)
        else:
            missing_skills.append(skill)

    # Core skill match percentage
    core_skills = role_config["core"]
    core_found = [s for s in core_skills if s in found_skills]
    core_ratio = len(core_found) / max(len(core_skills), 1)

    all_ratio = len(found_skills) / max(len(all_role_skills), 1)
    skills_score = int(min(100, max(20, (core_ratio * 70) + (all_ratio * 30))))

    # 2. ATS Formatting & Contact Information
    ats_score = 100
    ats_issues: List[str] = []

    has_email = bool(re.search(r"[\w\.-]+@[\w\.-]+\.\w+", cleaned_text))
    has_phone = bool(re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", cleaned_text))
    has_linkedin_or_github = bool(re.search(r"(linkedin\.com|github\.com)", lower_text))

    if not has_email:
        ats_score -= 20
        ats_issues.append("Missing email address")
    if not has_phone:
        ats_score -= 10
        ats_issues.append("Missing phone number")
    if not has_linkedin_or_github:
        ats_score -= 10
        ats_issues.append("Consider adding your GitHub or LinkedIn profile link")

    # Word count & length
    words = cleaned_text.split()
    word_count = len(words)
    if word_count < 150:
        ats_score -= 25
        ats_issues.append("Resume is too concise (< 150 words); expand on project details and achievements")
    elif word_count > 1200:
        ats_score -= 15
        ats_issues.append("Resume may exceed standard 1-2 page length (> 1200 words); summarize where possible")

    ats_score = max(20, min(100, ats_score))

    # 3. Structure & Section Check
    sections = {
        "Experience / Projects": bool(re.search(r"\b(experience|projects|work history|employment|internships?)\b", lower_text)),
        "Skills": bool(re.search(r"\b(skills|technical skills|technologies|tools|competencies)\b", lower_text)),
        "Education": bool(re.search(r"\b(education|academic|degree|university|college|b\.tech|bachelor|master)\b", lower_text)),
        "Summary / Profile": bool(re.search(r"\b(summary|profile|about me|objective|overview)\b", lower_text)),
        "Certifications / Achievements": bool(re.search(r"\b(certifications?|awards?|achievements?|honors?|courses?)\b", lower_text)),
    }

    found_sections_count = sum(1 for present in sections.values() if present)
    structure_score = int(min(100, (found_sections_count / len(sections)) * 100))

    # 4. Action Verbs & Quantifiable Impact
    found_action_verbs = []
    for verb in STRONG_ACTION_VERBS:
        if re.search(r"\b" + verb + r"\b", lower_text):
            found_action_verbs.append(verb)

    found_weak_phrases = []
    for phrase in WEAK_PHRASES:
        if phrase in lower_text:
            found_weak_phrases.append(phrase)

    # Detect numbers, percentages, currency, metrics (e.g. 40%, $10k, 500+ users, 2x faster)
    quantifiable_matches = re.findall(r"(\b\d+%\b|\$\d+[\w,.]*|\b\d+\+?\s*(users|clients|requests|ms|seconds|x|million|k|hours)\b)", lower_text)
    numbers_count = len(re.findall(r"\b\d+\b", cleaned_text))

    impact_score = 30
    impact_score += min(35, len(found_action_verbs) * 5)
    impact_score += min(35, (len(quantifiable_matches) * 10) + min(15, numbers_count * 2))
    impact_score -= len(found_weak_phrases) * 5
    impact_score = int(max(20, min(100, impact_score)))

    # 5. Overall ATS Score (Weighted)
    overall_score = int(
        (0.35 * skills_score) +
        (0.25 * ats_score) +
        (0.25 * impact_score) +
        (0.15 * structure_score)
    )
    overall_score = max(10, min(100, overall_score))

    # 6. Strengths, Weaknesses & Recommendations
    strengths: List[str] = []
    weaknesses: List[str] = []
    recommendations: List[str] = []

    if len(found_skills) >= 6:
        strengths.append(f"Strong alignment with {target_role} requirements, showcasing {len(found_skills)} relevant technical competencies.")
    else:
        weaknesses.append(f"Low density of core skills for {target_role} (only {len(found_skills)} detected).")
        recommendations.append(f"Incorporate missing core skills: {', '.join(missing_skills[:5])}.")

    if len(found_action_verbs) >= 5:
        strengths.append(f"Effective use of high-impact action verbs ({', '.join(found_action_verbs[:4])}).")
    else:
        weaknesses.append("Descriptions rely on passive language rather than strong action verbs.")
        recommendations.append("Begin bullet points with powerful action verbs like 'Architected', 'Spearheaded', 'Engineered', and 'Optimized'.")

    if len(quantifiable_matches) >= 2 or numbers_count >= 5:
        strengths.append("Includes measurable outcomes and metrics that demonstrate real-world impact.")
    else:
        weaknesses.append("Lack of quantifiable results (percentages, speed improvements, user scale).")
        recommendations.append("Quantify your achievements using metrics (e.g., 'Improved API latency by 35%', 'Served 1,000+ active users').")

    if sections["Education"] and sections["Skills"] and sections["Experience / Projects"]:
        strengths.append("Standard ATS-friendly section layout with clear headings.")
    else:
        missing_secs = [k for k, v in sections.items() if not v]
        weaknesses.append(f"Missing essential resume sections: {', '.join(missing_secs)}.")
        recommendations.append(f"Add explicit section headings for: {', '.join(missing_secs)}.")

    if found_weak_phrases:
        recommendations.append(f"Replace passive phrases like '{found_weak_phrases[0]}' with direct action statements.")

    # Section-by-section breakdown feedback
    section_feedback = {
        "summary": "Present and concise." if sections["Summary / Profile"] else "Add a 2-3 line professional summary highlighting your target role and core strengths.",
        "skills": f"{len(found_skills)} matching skills identified. Boost your ATS rank by adding {', '.join(missing_skills[:4])}." if missing_skills else "Great skill coverage for your role.",
        "experience_projects": "Descriptions have good detail." if len(found_action_verbs) >= 3 else "Add more depth to project bullet points using the STAR method (Situation, Task, Action, Result).",
        "education": "Education section recognized." if sections["Education"] else "Ensure your degree, institution, and graduation year are clearly listed.",
    }

    return {
        "overall_score": overall_score,
        "ats_compatibility": ats_score,
        "skills_score": skills_score,
        "impact_score": impact_score,
        "structure_score": structure_score,
        "found_keywords": found_skills,
        "missing_keywords": missing_skills[:12],
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations,
        "section_feedback": section_feedback,
        "word_count": word_count,
        "sections_detected": sections,
    }
