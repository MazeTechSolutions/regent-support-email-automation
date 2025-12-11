"""
Classification configuration - edit tags and examples here.
"""

CLASSIFICATION_TAGS = [
    {
        "name": "academic-results",
        "description": "Queries regarding the release of marks, viewing results on the portal, or missing marks.",
        "examples": [
            "When will the results for Financial Management be released?",
            "I can't view my results on the portal, are they out yet?",
            "My results are blocked but I have paid my fees.",
            "I am missing one exam result from my statement.",
            "I have not received my assignment results yet.",
            "When will the marks be visible on the portal?"
        ]
    },
    {
        "name": "academic-exam",
        "description": "Queries regarding final exams, supplementaries, Aegrotat (sick/missed exams), and exam interface formatting issues.",
        "examples": [
            "I missed my exam because I was in hospital, how do I apply for Aegrotat?",
            "I need to apply for the supplementary exam in January",
            "The exam interface didn't allow me to create tables",
            "I lost time due to network issues, will I be penalized?",
            "I submitted the wrong file for my exam"
        ]
    },
    {
        "name": "academic-assignment",
        "description": "Queries regarding coursework, assignment submission errors, extension requests, and marking disputes/feedback.",
        "examples": [
            "I submitted the wrong file for my WDA Economics assignment",
            "Why did the whole class get 35/70 with no feedback?",
            "My assignment marks are not showing on the portal",
            "Can I request a remark for my assignment?",
            "I missed the quiz deadline due to illness"
        ]
    },
    {
        "name": "admin-transcript",
        "description": "Requests for official/unofficial transcripts, academic records, and resolving transcript holds.",
        "examples": [
            "I have a transcript hold but my account is paid in full.",
            "Please send me my official transcript for a job application.",
            "I need to download my unofficial transcript but it says unavailable.",
            "Can I get a full year transcript sent to my employer?",
            "I need a letter of completion and my academic record.",
            "Why is there a hold on my transcript?"
        ]
    },
    {
        "name": "admin-graduation",
        "description": " inquiries about graduation ceremonies, dates, and collection of certificates.",
        "examples": [
            "When will the graduation details be shared?",
            "When and how can I collect my official degree certificate?",
            "Is the graduation ceremony taking place in Johannesburg?",
            "I have completed my degree, what are the next steps for graduation?",
            "Will I receive a digital certificate?"
        ]
    },
    {
        "name": "finance-payment",
        "description": "Issues related to payments made, proof of payment (POP) submission, refunds, and unblocking accounts.",
        "examples": [
            "Please find attached my proof of payment.",
            "I have paid my fees but my results are still blocked.",
            "I am on a bursary, why is my account showing arrears?",
            "I would like to request a refund for overpayment.",
            "Please allocate this payment to my student number.",
            "My employer has paid the fees, please update my account."
        ]
    },
    {
        "name": "finance-fees",
        "description": "Requests for invoices, fee statements, quotes, and balance inquiries.",
        "examples": [
            "How much do I currently owe on my account?",
            "Please send me a fee statement for the current year.",
            "I need a quote for my 3rd-year fees to send to my sponsor.",
            "Can I get a pro forma invoice for next year?",
            "Please advise on the fee amount to bring my account up to date."
        ]
    },
    {
        "name": "registration",
        "description": "Enrolling for new academic years, adding/repeating modules, and registration forms.",
        "examples": [
            "How do I register for the 2026 academic year?",
            "I need to re-register for a module I failed.",
            "Can you send me the registration form for the next semester?",
            "I want to register for a single module.",
            "What is the deadline to register for the second semester?"
        ]
    },
    {
        "name": "technical-proctoring",
        "description": "Urgent issues specifically related to SMOWL, camera failures, 'Error C-LS-1001', or being kicked out/freezing *during* an active exam.",
        "examples": [
            "My SMOWL says 'something went wrong contact administrator'",
            "Error C-LS-1001",
            "I was writing my exam and the screen disappeared",
            "My camera went off in the middle of the exam",
            "It says I am unregistered but I registered yesterday"
        ]
    },
    {
        "name": "technical-access",
        "description": "General login issues, password resets, and portal access problems NOT occurring during an active exam.",
        "examples": [
            "I cannot log into the student portal",
            "I cannot log into the myRegent app",
            "I cannot log into the myRegent website",
            "How do I reset my password?",
            "My profile is blocked",
            "I can't access the LMS to view my modules",
            "Do I need to register for Smowl again?"
        ]
    },
    {
        "name": "general-inquiry",
        "description": "Low-urgency information requests: Timetables, module codes, calendar dates, contact info.",
        "examples": [
            "Please provide module codes for Business Stats for my bursary",
            "Where can I find the exam timetable?",
            "What is the pass mark for this module?",
            "How do I calculate if I qualify for the exam?",
        ]
    },
    {
        "name": "complaint-escalation",
        "description": "Formal grievances, group complaints about lecturers/marking, or repeated service failures requiring management view.",
        "examples": [
            "I am writing on behalf of the 1st semester class regarding unfair marking",
            "We have sent multiple emails with no response regarding the feedback",
            "The lecturer is not responding to emails",
            "I am not satisfied with the service Regent is giving us"
        ]
    }
]


def get_classification_prompt():
    """Generate the classification prompt with current tags and examples."""
    tags_description = "\n".join([
        f"- **{tag['name']}**: {tag['description']}"
        for tag in CLASSIFICATION_TAGS
    ])

    examples_section = "\n\n".join([
        f"**{tag['name'].upper()}** examples:\n" +
        "\n".join([f'  - "{ex}"' for ex in tag['examples']])
        for tag in CLASSIFICATION_TAGS
    ])

    valid_tags = ", ".join([tag['name'] for tag in CLASSIFICATION_TAGS])

    return f"""You are an email classification assistant for Regent University student support.
Your task is to classify incoming emails into one of the following categories:

{tags_description}

Here are examples for each category:

{examples_section}

IMPORTANT - HANDLING EMAIL THREADS:
- The email body may contain a conversation thread with previous messages (quoted replies, forwarded content, etc.)
- You must ONLY classify based on the MOST RECENT/NEWEST message (typically at the top)
- Use the conversation history ONLY as context to better understand the current request
- Do NOT classify based on older messages in the thread
- Look for indicators like "On [date], [person] wrote:", "From:", "-----Original Message-----", or ">" quote markers to identify older messages

INSTRUCTIONS:
1. Identify the MOST RECENT message in the email (ignore quoted/forwarded older content)
2. Read the subject and the latest message carefully
3. Determine the PRIMARY intent of the latest message only
4. Select the SINGLE most appropriate category
5. Provide a confidence score (0.0 to 1.0)
6. Give a brief reason for your classification

RESPOND IN EXACTLY THIS JSON FORMAT (no markdown, no code blocks):
{{"classification": "<tag_name>", "confidence": <0.0-1.0>, "reason": "<brief explanation>"}}

Valid tags: {valid_tags}

If the email is ambiguous, choose the category that best matches the main request.
If truly unclear, use "general-inquiry" with lower confidence."""
