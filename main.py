#!/usr/bin/env python3
"""
Main entry point for the Agentic SDLC POC.

Demonstrates running the three agents: Architect, Developer, and Reviewer.
"""

import json
import sys
from dotenv import load_dotenv
from agents import ArchitectAgent, DeveloperAgent, ReviewerAgent

load_dotenv()


def demo_architect_agent():
    """Demo: Architect Agent analyzing service architecture."""
    print("\n" + "="*80)
    print("DEMO 1: Architect Agent - Service Architecture Analysis")
    print("="*80)

    agent = ArchitectAgent()

    user_input = """
    We need to build a new Payment Processing service. The service should:
    1. Accept payment requests from the API Gateway
    2. Validate payment details
    3. Communicate with the Billing service for invoice updates
    4. Store transaction history in a database

    Query Port to understand how existing services (like Order Service, Billing Service)
    are structured, what tech stacks they use, and who owns them. Then provide a
    recommended architecture for the Payment Processing service.
    """

    print(f"\nUser Input:\n{user_input}\n")
    response = agent.run(user_input, max_iterations=5)

    print(f"\n[Architect Agent] Final Response:\n{response}\n")
    return response


def demo_developer_agent():
    """Demo: Developer Agent working on a feature."""
    print("\n" + "="*80)
    print("DEMO 2: Developer Agent - Feature Implementation")
    print("="*80)

    agent = DeveloperAgent()

    user_input = """
    I have a Jira ticket (PAYMENT-42) to implement.

    Ticket: "Add support for recurring payments in the Payment service"
    Requirements:
    - Store recurring payment schedules
    - Implement a cron job to process recurring payments
    - Return subscription ID on creation
    - Support cancellation of recurring payments

    First, query Port to understand the Payment service's current structure and
    dependencies. Then generate a plan and code skeleton for implementing this feature.
    """

    print(f"\nUser Input:\n{user_input}\n")
    response = agent.run(user_input, max_iterations=5)

    print(f"\n[Developer Agent] Final Response:\n{response}\n")
    return response


def demo_reviewer_agent():
    """Demo: Reviewer Agent reviewing a pull request."""
    print("\n" + "="*80)
    print("DEMO 3: Reviewer Agent - Code Review")
    print("="*80)

    agent = ReviewerAgent()

    user_input = """
    Please review the following pull request for the Payment Service:

    Changes made:
    1. Added RecurringPayment model with schedule fields
    2. Created /api/recurring-payments POST endpoint
    3. Added background job to process recurring payments every hour
    4. No tests added yet
    5. Database migration added (not rolled back)

    Key code snippets:
    - Database query: "SELECT * FROM recurring_payments WHERE status='active'"
    - API endpoint stores user_id directly in payment record without validation
    - Background job retries indefinitely on failure

    Query Port to understand the Payment service's standards and dependencies.
    Then provide a comprehensive security and quality review.
    """

    print(f"\nUser Input:\n{user_input}\n")
    response = agent.run(user_input, max_iterations=5)

    print(f"\n[Reviewer Agent] Final Response:\n{response}\n")
    return response


def main():
    """Run all demos or a specific one."""
    if len(sys.argv) > 1:
        demo_name = sys.argv[1].lower()
        if demo_name == "architect":
            demo_architect_agent()
        elif demo_name == "developer":
            demo_developer_agent()
        elif demo_name == "reviewer":
            demo_reviewer_agent()
        else:
            print(f"Unknown demo: {demo_name}")
            print("Available demos: architect, developer, reviewer")
    else:
        print("Agentic SDLC POC - Core Agent Foundation")
        print("\nUsage: python main.py [architect|developer|reviewer]")
        print("\nExample: python main.py architect")
        print("\nRunning all demos...\n")

        demo_architect_agent()
        demo_developer_agent()
        demo_reviewer_agent()

        print("\n" + "="*80)
        print("All demos completed!")
        print("="*80)


if __name__ == "__main__":
    main()
