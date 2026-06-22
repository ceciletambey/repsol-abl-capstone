"""
Assessment content and scoring — ported from the baseline assessment HTML
so the Streamlit app and the Evaluator's generated re-assessment both
score answers with the exact same rule.
"""

import math

CATEGORIES = [
    {
        "id": "digcomp",
        "label": "General Digital Competency",
        "questions": [
            {
                "type": "self_report",
                "text": "When you receive a document or file at work, how do you decide whether the information in it is reliable?",
                "options": [
                    "I cross-reference it with other sources and check the date and author.",
                    "I usually trust it if it comes from a work email.",
                    "I apply a structured fact-checking process and can coach others on evaluating digital sources.",
                    "I check who sent it and whether it looks official.",
                ],
                "scores": [3, 1, 4, 2],
            },
            {
                "type": "self_report",
                "text": "A colleague asks you to collaborate on a document in real time using a cloud tool. What best describes your experience?",
                "options": [
                    "I have done it a few times with help.",
                    "I set up and govern shared workspaces and train others to use them.",
                    "I have heard of it but have not done it before.",
                    "I do it regularly and manage version history and permissions comfortably.",
                ],
                "scores": [2, 4, 1, 3],
            },
            {
                "type": "knowledge_check",
                "text": "What does the term 'digital footprint' mean in a professional context?",
                "options": [
                    "The storage space used by files on your work computer.",
                    "The trail of data you leave behind through your online activity — websites visited, emails sent, and information shared.",
                    "A type of malware that tracks your keyboard input.",
                    "The battery consumption of your device during a workday.",
                ],
                "correct": 1,
                "explanation": "A digital footprint includes all data traces left by your online actions.",
            },
        ],
    },
    {
        "id": "data",
        "label": "Data Literacy",
        "questions": [
            {
                "type": "self_report",
                "text": "A manager shares a chart showing monthly sales trends. Which best describes how you interpret it?",
                "options": [
                    "I critique the chart design, suggest improvements, and derive actionable insights for decision-making.",
                    "I understand the trend and can describe what it shows.",
                    "I can read the basic numbers but struggle to draw conclusions.",
                    "I interpret the trend, spot anomalies, and link it to business context.",
                ],
                "scores": [4, 2, 1, 3],
            },
            {
                "type": "self_report",
                "text": "Which best describes your experience working with datasets or data tools?",
                "options": [
                    "I clean, transform, and combine data from multiple sources independently.",
                    "I work mainly with Excel spreadsheets with small amounts of data.",
                    "I build ETL pipelines, write complex queries (SQL, Python, etc.), and design data models.",
                    "I can filter, sort, and do basic calculations on structured datasets.",
                ],
                "scores": [3, 1, 4, 2],
            },
            {
                "type": "knowledge_check",
                "text": "Which of the following is the best example of data governance in practice?",
                "options": [
                    "Choosing a bar chart instead of a pie chart for a presentation.",
                    "Defining who can access, modify, and delete a dataset, and setting data quality standards.",
                    "Training a machine learning model on customer data.",
                    "Exporting a Power BI report to PDF and emailing it to your team.",
                ],
                "correct": 1,
                "explanation": "Data governance is about defining ownership, access rules, and quality standards for data.",
            },
        ],
    },
    {
        "id": "ia_gen",
        "label": "Generative AI & Copilot",
        "questions": [
            {
                "type": "self_report",
                "text": "How would you describe your current use of generative AI tools (e.g., Copilot Web, ChatGPT) in your work?",
                "options": [
                    "I use them occasionally for simple tasks like drafting emails or summarising text.",
                    "I design prompt frameworks, integrate AI into workflows, and guide others on effective use.",
                    "I have not used them or have only tried them out of curiosity.",
                    "I use them regularly and adapt my prompts to get specific, high-quality outputs.",
                ],
                "scores": [2, 4, 1, 3],
            },
            {
                "type": "self_report",
                "text": "How aware are you of the risks of using generative AI at work (e.g., hallucinations, data confidentiality, bias)?",
                "options": [
                    "I apply a responsible AI framework, contribute to usage policies, and train colleagues on safe AI practices.",
                    "I am not aware of specific risks.",
                    "I actively verify AI outputs, avoid inputting confidential data, and consider bias in responses.",
                    "I know AI can make mistakes and I should not share sensitive data.",
                ],
                "scores": [4, 1, 3, 2],
            },
            {
                "type": "knowledge_check",
                "text": "Which of the following is the best practice when writing a prompt for Copilot or another generative AI tool?",
                "options": [
                    "Keep it as short and vague as possible so the AI has creative freedom.",
                    "Always write in English, even if your work language is different.",
                    "Provide clear context, specify the format and length you want, and state the tone or audience.",
                    "Include your personal login credentials so the AI can access your account data.",
                ],
                "correct": 2,
                "explanation": "Effective prompting means giving the AI enough context — this is the basis of Repsol's 6 Ps prompting method.",
            },
        ],
    },
    {
        "id": "automation",
        "label": "Automation",
        "questions": [
            {
                "type": "self_report",
                "text": "Think of a repetitive task you do regularly. How do you handle it?",
                "options": [
                    "I use a tool like Power Automate to automate it end-to-end.",
                    "I design and deploy automated workflows across systems and mentor others on automation.",
                    "I do it manually every time.",
                    "I have tried basic features like Excel macros or scheduled emails.",
                ],
                "scores": [3, 4, 1, 2],
            },
            {
                "type": "self_report",
                "text": "How familiar are you with no-code or low-code automation platforms (e.g., Microsoft Power Automate)?",
                "options": [
                    "I design complex multi-step automations, connect APIs, and handle error management.",
                    "I know they exist and have seen a demo or tried a simple flow.",
                    "I have not heard of or used them.",
                    "I build and maintain automation flows independently.",
                ],
                "scores": [4, 2, 1, 3],
            },
            {
                "type": "knowledge_check",
                "text": "In Microsoft Power Automate, what is a 'trigger'?",
                "options": [
                    "A button you press to manually stop a running flow.",
                    "The event that starts an automated workflow (e.g., a new email arrives or a file is uploaded to SharePoint).",
                    "An error message displayed when a flow fails.",
                    "A summary report generated at the end of a completed workflow.",
                ],
                "correct": 1,
                "explanation": "A trigger is the starting event of an automated flow.",
            },
        ],
    },
    {
        "id": "power_bi",
        "label": "Data Visualisation (Power BI)",
        "questions": [
            {
                "type": "self_report",
                "text": "A Power BI dashboard has been shared with you. Which best describes what you can do with it?",
                "options": [
                    "I can use filters, explore tabs, and export data.",
                    "I can evaluate the report design and suggest structural or DAX formula improvements to the creator.",
                    "I navigate confidently, slice data by different dimensions, and subscribe to report alerts.",
                    "I can view it but do not know how to use filters or drill down into data.",
                ],
                "scores": [2, 4, 3, 1],
            },
            {
                "type": "self_report",
                "text": "Have you ever built a Power BI report (connecting to a data source, transforming data, creating visuals)?",
                "options": [
                    "I build reports independently, including data transformation and table relationships.",
                    "No, I have only ever viewed reports built by others.",
                    "I build complex models with advanced DAX, Row-Level Security, and publish to shared workspaces.",
                    "I have built a basic report following a tutorial or with guidance.",
                ],
                "scores": [3, 1, 4, 2],
            },
            {
                "type": "knowledge_check",
                "text": "What does DAX stand for, and what is it used for in Power BI?",
                "options": [
                    "Digital Analytics Exchange — a protocol for exporting Power BI reports.",
                    "Data Analysis Expressions — a formula language used to create calculated columns, measures, and custom aggregations in Power BI.",
                    "Dashboard and Excel — a feature for importing Excel files into Power BI.",
                    "Data Aggregation Extension — a plug-in that connects Power BI to external databases.",
                ],
                "correct": 1,
                "explanation": "DAX (Data Analysis Expressions) is Power BI's formula language.",
            },
        ],
    },
    {
        "id": "m365",
        "label": "Microsoft 365 & Digital Workplace",
        "questions": [
            {
                "type": "self_report",
                "text": "Which best describes how you use Microsoft Teams in your day-to-day work?",
                "options": [
                    "I configure Teams environments, set governance policies, and integrate tools for my team.",
                    "I use channels, share files, and schedule meetings through Teams.",
                    "I mainly use it for video calls and basic chat.",
                    "I use Teams apps, tabs, and integrations (e.g., Planner, Forms) to manage work.",
                ],
                "scores": [4, 2, 1, 3],
            },
            {
                "type": "self_report",
                "text": "How do you typically manage and share documents with colleagues?",
                "options": [
                    "I save files to OneDrive or SharePoint and share a link.",
                    "I co-author documents in real time, manage permissions, and use version history.",
                    "I design SharePoint site structures, set document lifecycle policies, and train others.",
                    "I send files as email attachments.",
                ],
                "scores": [2, 3, 4, 1],
            },
            {
                "type": "knowledge_check",
                "text": "In Microsoft Teams, what is the main purpose of a 'Channel'?",
                "options": [
                    "A private one-to-one video call between two colleagues.",
                    "A company-wide announcement board only IT administrators can post to.",
                    "An organised space within a Team for focused conversations, file sharing, and collaboration on a specific topic or project.",
                    "A tool for scheduling meetings directly from Outlook.",
                ],
                "correct": 2,
                "explanation": "Channels keep Teams organised around a specific topic.",
            },
        ],
    },
    {
        "id": "cybersecurity",
        "label": "Cybersecurity Awareness",
        "questions": [
            {
                "type": "self_report",
                "text": "You receive an urgent email appearing to be from Repsol IT, asking you to click a link and reset your password immediately. What do you do?",
                "options": [
                    "I do not click the link, verify through official IT channels, and report it as a phishing attempt.",
                    "I click the link because it looks urgent and official.",
                    "I report it with full email headers to the security team and brief my team on the specific threat.",
                    "I hesitate and ask a colleague if they received the same email.",
                ],
                "scores": [3, 1, 4, 2],
            },
            {
                "type": "self_report",
                "text": "When working remotely, how do you protect company data?",
                "options": [
                    "I enforce and communicate remote security policies for my team and conduct security awareness sessions.",
                    "I connect to whatever Wi-Fi is available and work as normal.",
                    "I use VPN, lock my screen when away, avoid public Wi-Fi, and follow Repsol's remote work security policy.",
                    "I use the company VPN and avoid working in very public places.",
                ],
                "scores": [4, 1, 3, 2],
            },
            {
                "type": "knowledge_check",
                "text": "What is multi-factor authentication (MFA) and why is it important?",
                "options": [
                    "Using multiple different web browsers to access company systems, to avoid tracking.",
                    "A security method requiring more than one form of verification (e.g., password + a code sent to your phone) to access an account.",
                    "Having several different passwords saved for the same account as a backup.",
                    "An advanced antivirus software automatically installed by the IT department.",
                ],
                "correct": 1,
                "explanation": "MFA adds a second layer of security beyond the password.",
            },
        ],
    },
]

# Repsol's Target Skills Matrix (IE ABL Clarificacions PDF) — required level
# per role, mapped to assessment category ids. EXCEL and SAP have no
# corresponding assessment category, so they're not represented here; the
# matrix also defines no target for power_bi, so it stays absolute-scored.
ROLES = {
    "Training Team": {"data": 3, "automation": 1, "ia_gen": 2, "digcomp": 4, "m365": 3, "cybersecurity": 1},
    "Marketing Teams": {"data": 3, "automation": 1, "ia_gen": 3, "digcomp": 4, "m365": 3, "cybersecurity": 1},
    "Financial Services Team": {"data": 3, "automation": 2, "ia_gen": 2, "digcomp": 4, "m365": 3, "cybersecurity": 2},
    "Buyers": {"data": 3, "automation": 1, "ia_gen": 2, "digcomp": 4, "m365": 3, "cybersecurity": 2},
    "IT Professional": {"data": 3, "automation": 4, "ia_gen": 3, "digcomp": 4, "m365": 4, "cybersecurity": 3},
}

# Order must match the 4 options of the "priority_skill" PD question below.
PD_PRIORITY_IDS = ["ai_ml", "data_bi", "security", "collaboration"]

PD_QUESTIONS = [
    {
        "id": "pd_areas",
        "type": "multi_select",
        "text": "Which skill areas would you like to develop beyond what your current role requires?",
        "options": [
            "Data Science & Advanced Analytics", "Generative AI & Prompt Engineering",
            "Cloud Computing & Architecture", "Cybersecurity & Risk Management",
            "Leadership & Digital Transformation", "Project Management & Agile Methodologies",
            "Programming & Software Development", "Business Intelligence & Data Visualisation",
        ],
    },
    {
        "id": "pd_motivation",
        "type": "single_select",
        "text": "What best describes your primary motivation for developing skills beyond your current role?",
        "options": [
            "Preparing for a promotion within my current department",
            "Exploring a potential career change to a different function at Repsol",
            "Personal interest and curiosity — I enjoy learning new technologies",
            "Staying competitive and relevant as the industry evolves",
        ],
    },
    {
        "id": "pd_format",
        "type": "single_select",
        "text": "How would you prefer to receive optional learning content for personal development?",
        "options": [
            "Short daily nudges I can complete in under 10 minutes",
            "Weekly self-paced modules I can schedule around my work",
            "Intensive workshops or structured bootcamps",
            "Unscheduled deep-dives that I initiate when I feel motivated",
        ],
    },
    {
        "id": "pd_digital_habits",
        "type": "single_select",
        "text": "Which statement best describes your relationship with digital technology outside of work?",
        "options": [
            "I use only what is needed for daily life — nothing beyond the basics",
            "I occasionally try new apps or tools when a friend recommends them",
            "I actively follow tech trends and experiment with new tools regularly",
            "I build, customise, or code digital tools as a personal hobby",
        ],
    },
    {
        "id": "pd_priority_skill",
        "type": "single_select",
        "text": "If the system could accelerate your growth in one domain over the next six months, which would you choose?",
        "options": [
            "Artificial Intelligence & Machine Learning",
            "Data Analysis & Business Intelligence",
            "Digital Security & Privacy",
            "Collaboration, Productivity & Workplace Tools",
        ],
    },
]


def score_questions(questions, answers):
    """Apply the assessment's scoring rule to any list of answered questions:
    floor(avg score), capped at 2 if a knowledge check was wrong while the
    self-report average was confident (>=3)."""
    scores = [
        q["scores"][a] if q["type"] == "self_report" else (3 if a == q["correct"] else 1)
        for q, a in zip(questions, answers)
    ]
    sr_scores = [s for q, s in zip(questions, scores) if q["type"] == "self_report"]
    kc_scores = [s for q, s in zip(questions, scores) if q["type"] == "knowledge_check"]

    final = math.floor(sum(scores) / len(scores))
    sr_avg = sum(sr_scores) / len(sr_scores) if sr_scores else None
    kc_wrong = any(s == 1 for s in kc_scores)
    overconfident = kc_wrong and sr_avg is not None and sr_avg >= 3
    if overconfident:
        final = min(final, 2)
    final = max(1, min(4, final))

    return {
        "final": final,
        "knowledge_gap": overconfident,
        "immediate_nudge": final == 1,
    }


def build_footprint(category_answers, pd_answers, role=None):
    """category_answers: {cat_id: [a0, a1, a2]}. pd_answers: {"pd_areas": [...], "pd_priority_skill": idx|None}.
    role: a key into ROLES — embeds each category's required_level for that role,
    so a gap can be measured against the job's actual requirement, not an
    absolute scale."""
    required = ROLES.get(role, {})
    footprint = {}
    for cat in CATEGORIES:
        result = score_questions(cat["questions"], category_answers[cat["id"]])
        entry = {"level": result["final"], "knowledge_gap": result["knowledge_gap"]}
        if cat["id"] in required:
            entry["required_level"] = required[cat["id"]]
        footprint[cat["id"]] = entry

    priority_idx = pd_answers.get("pd_priority_skill")
    if priority_idx is not None:
        footprint["personal_development"] = {"priority_skill": PD_PRIORITY_IDS[priority_idx]}

    return footprint
