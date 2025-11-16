"""
Generate mock enterprise documents for testing

This script creates realistic enterprise documents mimicking:
- ServiceNow KB articles
- SharePoint HR policies
- Confluence documentation
- Learning portal content
"""
import json
import os
from datetime import datetime, timedelta
import random

# Mock data sources
SERVICENOW_ARTICLES = [
    {
        "title": "How to Request Time Off",
        "content": """
        To request time off, follow these steps:

        1. Navigate to the Employee Portal (https://portal.company.com)
        2. Click on 'Leave Management' in the HR section
        3. Select 'Request Time Off'
        4. Choose the type of leave (Annual Leave, Sick Leave, Personal Day)
        5. Select the dates and add a reason
        6. Submit for manager approval

        Important notes:
        - Requests must be submitted at least 2 weeks in advance for annual leave
        - Manager approval is required for all leave requests
        - Check your leave balance before requesting
        - For urgent sick leave, notify your manager directly

        For questions, contact HR at hr@company.com or extension 5555.
        """,
        "country_tags": ["UK", "US", "DE"],
        "department": "HR",
        "tags": ["leave", "time-off", "vacation", "pto"],
        "acl_allow": ["all-employees"]
    },
    {
        "title": "Setting Up Your Development Environment",
        "content": """
        New developers should set up their environment as follows:

        Required Software:
        - Git (version 2.30+)
        - Docker Desktop
        - Visual Studio Code or IntelliJ IDEA
        - Node.js 18 LTS
        - Python 3.10+

        Setup Steps:
        1. Clone the main repository: git clone https://github.com/company/main-app.git
        2. Install dependencies: npm install && pip install -r requirements.txt
        3. Configure environment variables (copy .env.example to .env)
        4. Start local services: docker-compose up -d
        5. Run tests to verify setup: npm test

        Access:
        - VPN: Use Cisco AnyConnect (credentials from IT)
        - Internal npm registry: Configure with .npmrc
        - AWS credentials: Request from DevOps team

        For issues, contact #dev-support on Slack.
        """,
        "country_tags": ["US"],
        "department": "Engineering",
        "tags": ["development", "setup", "onboarding", "tools"],
        "acl_allow": ["all-employees", "us-engineering"]
    },
    {
        "title": "Remote Work Policy",
        "content": """
        Company Remote Work Policy (Effective Jan 2024)

        Eligibility:
        - All employees in eligible roles may work remotely up to 3 days per week
        - Managers may approve additional remote days case-by-case
        - Some roles (e.g., facilities, reception) require on-site presence

        Requirements:
        - Maintain availability during core hours (10am-3pm local time)
        - Attend mandatory in-office days (Tuesdays and Thursdays)
        - Ensure adequate home internet (min 25 Mbps)
        - Use company-approved VPN and security tools

        Equipment:
        - Laptop and peripherals provided by IT
        - Home office stipend: £500/year for UK, $600/year for US
        - Ergonomic assessment available on request

        Best Practices:
        - Update calendar with WFH days
        - Keep camera on for team meetings
        - Respond to messages within 2 hours during work hours
        - Secure your workspace and lock devices when away

        Questions? Contact HR-Benefits@company.com
        """,
        "country_tags": ["UK", "US"],
        "department": "HR",
        "tags": ["remote-work", "wfh", "policy", "flexible-working"],
        "acl_allow": ["all-employees"]
    },
    {
        "title": "Expense Reimbursement Process",
        "content": """
        How to Submit Expense Reimbursements:

        Eligible Expenses:
        - Travel (flights, trains, taxis)
        - Accommodation
        - Client meals and entertainment
        - Office supplies (if pre-approved)
        - Professional development (with manager approval)

        Submission Process:
        1. Log into Concur: https://concur.company.com
        2. Create new expense report
        3. Attach receipts (required for expenses >$25)
        4. Categorize each expense correctly
        5. Add business justification
        6. Submit for approval

        Approval Timeline:
        - Manager approval: 3-5 business days
        - Finance review: 2-3 business days
        - Reimbursement: Next payroll cycle

        Limits:
        - Meals: $50/day (domestic), $75/day (international)
        - Hotels: Company rate or $200/night max
        - Alcohol: Not reimbursable unless client entertainment

        For urgent reimbursements, contact finance-ap@company.com
        """,
        "country_tags": ["UK", "US", "DE"],
        "department": "Finance",
        "tags": ["expenses", "reimbursement", "travel", "concur"],
        "acl_allow": ["all-employees"]
    }
]

SHAREPOINT_POLICIES = [
    {
        "title": "Code of Conduct and Ethics Policy",
        "content": """
        Company Code of Conduct - All Employees

        Our Values:
        - Integrity: Act honestly and ethically in all business dealings
        - Respect: Treat all colleagues, clients, and partners with dignity
        - Excellence: Deliver high-quality work and continuous improvement
        - Collaboration: Work together towards common goals

        Professional Standards:
        - Comply with all applicable laws and regulations
        - Maintain confidentiality of company and client information
        - Avoid conflicts of interest and disclose potential conflicts
        - Represent the company professionally at all times

        Prohibited Conduct:
        - Harassment or discrimination of any kind
        - Misuse of company resources
        - Insider trading or market manipulation
        - Bribery or improper payments
        - Retaliation against whistleblowers

        Reporting Violations:
        - Speak to your manager or HR Business Partner
        - Use anonymous ethics hotline: 1-800-ETHICS-1
        - Email ethics@company.com

        Violations may result in disciplinary action up to and including termination.

        All employees must acknowledge this policy annually.
        """,
        "country_tags": ["UK", "US", "DE", "FR"],
        "department": "HR",
        "tags": ["policy", "ethics", "conduct", "compliance"],
        "acl_allow": ["all-employees"]
    },
    {
        "title": "Data Protection and Privacy Policy (GDPR)",
        "content": """
        Data Protection Policy - GDPR Compliance

        Scope:
        This policy applies to all employees handling personal data of EU residents.

        Principles:
        1. Lawfulness, fairness, and transparency
        2. Purpose limitation - collect data only for specified purposes
        3. Data minimization - collect only necessary data
        4. Accuracy - keep data up to date
        5. Storage limitation - retain only as long as needed
        6. Integrity and confidentiality - secure data appropriately

        Employee Responsibilities:
        - Complete annual GDPR training
        - Process personal data only as authorized
        - Report data breaches within 24 hours
        - Respond to data subject requests within required timeframes
        - Secure personal data with encryption and access controls

        Data Subject Rights:
        - Right to access
        - Right to rectification
        - Right to erasure ("right to be forgotten")
        - Right to data portability
        - Right to object to processing

        Handling Personal Data:
        - Store in approved systems only (no personal drives/emails)
        - Encrypt when transmitting
        - Delete securely when no longer needed
        - Never share with unauthorized parties

        Data Breach Response:
        1. Immediately notify DPO: dpo@company.com
        2. Document the breach details
        3. Assist in breach investigation
        4. Follow remediation instructions

        For questions, contact the Data Protection Officer.
        """,
        "country_tags": ["UK", "DE", "FR"],
        "department": "Legal",
        "tags": ["gdpr", "privacy", "data-protection", "compliance"],
        "acl_allow": ["all-employees", "uk-legal", "de-legal"]
    }
]

LEARNING_CONTENT = [
    {
        "title": "Introduction to Kubernetes",
        "content": """
        Kubernetes Training - Module 1: Introduction

        What is Kubernetes?
        Kubernetes (K8s) is an open-source container orchestration platform for automating
        deployment, scaling, and management of containerized applications.

        Key Concepts:

        1. Pods
        - Smallest deployable unit in Kubernetes
        - Can contain one or more containers
        - Share network and storage

        2. Deployments
        - Declare desired state for Pods
        - Handle rolling updates and rollbacks
        - Ensure specified number of replicas

        3. Services
        - Expose Pods to network traffic
        - Load balance across Pod replicas
        - Types: ClusterIP, NodePort, LoadBalancer

        4. ConfigMaps and Secrets
        - ConfigMaps: Non-sensitive configuration
        - Secrets: Sensitive data (passwords, tokens)

        Architecture:
        - Control Plane: API server, scheduler, controller manager
        - Worker Nodes: Run containerized applications
        - etcd: Distributed key-value store

        Basic Commands:
        - kubectl get pods: List pods
        - kubectl describe pod <name>: Pod details
        - kubectl logs <pod>: View logs
        - kubectl apply -f <file>: Deploy resources

        Next Steps:
        Complete hands-on lab: Deploy a sample application to our dev cluster

        Questions? Join #k8s-learning on Slack
        """,
        "country_tags": ["US", "UK"],
        "department": "Engineering",
        "tags": ["kubernetes", "training", "containers", "devops"],
        "acl_allow": ["all-employees", "us-engineering", "uk-engineering"]
    }
]

def generate_mock_dataset(output_dir="data/mock"):
    """Generate mock enterprise documents"""
    os.makedirs(output_dir, exist_ok=True)

    all_documents = []
    doc_id = 1

    # Generate ServiceNow articles
    for article in SERVICENOW_ARTICLES:
        doc = {
            "source": "servicenow",
            "source_id": f"KB{str(doc_id).zfill(7)}",
            "title": article["title"],
            "content": article["content"].strip(),
            "url": f"https://company.service-now.com/kb_view.do?sysparm_article=KB{str(doc_id).zfill(7)}",
            "content_type": "text/html",
            "acl_allow": article["acl_allow"],
            "country_tags": article["country_tags"],
            "department": article["department"],
            "tags": article["tags"],
            "metadata": {
                "author": "KB Admin",
                "created": (datetime.now() - timedelta(days=random.randint(30, 365))).isoformat(),
                "category": "Knowledge Base"
            }
        }
        all_documents.append(doc)
        doc_id += 1

    # Generate SharePoint policies
    for policy in SHAREPOINT_POLICIES:
        doc = {
            "source": "sharepoint",
            "source_id": f"POL-{str(doc_id).zfill(5)}",
            "title": policy["title"],
            "content": policy["content"].strip(),
            "url": f"https://company.sharepoint.com/sites/hr/policies/{doc_id}.pdf",
            "content_type": "application/pdf",
            "acl_allow": policy["acl_allow"],
            "country_tags": policy["country_tags"],
            "department": policy["department"],
            "tags": policy["tags"],
            "metadata": {
                "author": "HR Policy Team",
                "created": (datetime.now() - timedelta(days=random.randint(60, 730))).isoformat(),
                "version": "2.1"
            }
        }
        all_documents.append(doc)
        doc_id += 1

    # Generate Learning content
    for content in LEARNING_CONTENT:
        doc = {
            "source": "learning",
            "source_id": f"LRN-{str(doc_id).zfill(5)}",
            "title": content["title"],
            "content": content["content"].strip(),
            "url": f"https://learn.company.com/courses/{doc_id}",
            "content_type": "text/markdown",
            "acl_allow": content["acl_allow"],
            "country_tags": content["country_tags"],
            "department": content["department"],
            "tags": content["tags"],
            "metadata": {
                "author": "Learning & Development",
                "created": (datetime.now() - timedelta(days=random.randint(10, 180))).isoformat(),
                "duration_minutes": 45
            }
        }
        all_documents.append(doc)
        doc_id += 1

    # Save to JSON
    output_file = os.path.join(output_dir, "enterprise_documents.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_documents, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(all_documents)} mock documents")
    print(f"Saved to: {output_file}")
    print(f"\nBreakdown:")
    print(f"  ServiceNow KB: {len(SERVICENOW_ARTICLES)}")
    print(f"  SharePoint Policies: {len(SHAREPOINT_POLICIES)}")
    print(f"  Learning Content: {len(LEARNING_CONTENT)}")

    return all_documents


if __name__ == "__main__":
    generate_mock_dataset()
