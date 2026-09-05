"""
Fake test data: a handful of synthetic transcripts covering each call type
and the edge cases the spec cares about most -- cease-and-desist, legal
mention, wrong number, profanity, missing owner, vague/unresolvable dates,
and a clean "nothing wrong" call as a control.

None of this is real customer data -- every name, company, and account
number here is made up for testing purposes only.
"""

# --------------------------------------------------------------------------
# 1. Collections call -- the spec's own scenario, extended with a
#    cease-and-desist near the end so both trigger paths get exercised.
# --------------------------------------------------------------------------
COLLECTIONS_CALL = {
    "call_id": "call_collections_001",
    "call_date": "2026-07-01",  # Wednesday
    "call_type": "collections",
    "customer_id": "cust_00123",
    "transcript": """
1: Agent: Hi, this is Marcus from Alpine Recovery calling about your account. Is this James?
2: Consumer: Yeah, this is James.
3: Agent: This call is being recorded for quality purposes. Your account balance is $1,400, past due since May.
4: Consumer: I know, things have been tight. I lost my job in April.
5: Agent: I understand. We can work out a payment plan. What can you manage?
6: Agent: The standard plan would be $1,400 in one payment, or two payments of $700 each.
7: Consumer: That's still too much right now. Could I do $700 now and $700 next month?
8: Agent: Let me note that -- $700 today and $700 on the 15th of next month. I'll need a supervisor to approve the settlement split, I'll follow up by Friday.
9: Consumer: Okay, that works. Just don't call me at work anymore, please.
10: Agent: Understood, I'll note to only call this number after 6pm.
""",
}

# --------------------------------------------------------------------------
# 2. Collections call gone wrong -- legal mention + bankruptcy + explicit
#    cease-and-desist, all in one call. Should trigger heavy human review.
# --------------------------------------------------------------------------
COLLECTIONS_ESCALATION_CALL = {
    "call_id": "call_collections_002",
    "call_date": "2026-07-08",  # Wednesday
    "call_type": "collections",
    "customer_id": "cust_00456",
    "transcript": """
1: Agent: Hi, this is Priya calling from Alpine Recovery regarding your outstanding balance of $2,300.
2: Consumer: I already told you guys not to call me at work anymore.
3: Agent: I apologize, I'll update our records. Can we discuss the balance?
4: Consumer: I filed for bankruptcy last month, you shouldn't even be calling.
5: Agent: I see, I'll need to verify that with our compliance team before continuing.
6: Consumer: If you call me again I will sue you, contact my attorney from now on.
7: Agent: Understood. I'm going to pause this account and escalate to a supervisor today.
8: Consumer: Fine. Also this is bullshit, I already sent proof of bankruptcy last week.
""",
}

# --------------------------------------------------------------------------
# 3. Support call -- vague date, no clear owner on one item, wrong number.
# --------------------------------------------------------------------------
SUPPORT_CALL = {
    "call_id": "call_support_001",
    "call_date": "2026-07-15",  # Wednesday
    "call_type": "support",
    "customer_id": "cust_00789",
    "transcript": """
1: Agent: Thanks for calling TechHelp support, this is Dana. How can I help?
2: Customer: Hi, my account keeps logging me out every few minutes.
3: Agent: Sorry about that. Let me pull up your account. Can I get your email?
4: Customer: Wait, actually -- is this TechHelp? I think I meant to call BrightSoft, wrong number.
5: Agent: No problem, this is TechHelp, happy to help if you'd like, or I can let you go.
6: Customer: Actually since I'm here -- I've had this logout issue for weeks, can someone look into it?
7: Agent: I'll escalate this to engineering, they'll take a look at some point.
8: Customer: Okay, and can you also credit my account for the downtime?
9: Agent: I don't have authorization for account credits above $20, I'll need to check with my manager.
""",
}

# --------------------------------------------------------------------------
# 4. Sales call -- discount beyond policy (compliance judgment call),
#    clear decision, clear action item.
# --------------------------------------------------------------------------
SALES_CALL = {
    "call_id": "call_sales_001",
    "call_date": "2026-07-20",  # Monday
    "call_type": "sales",
    "customer_id": "cust_01011",
    "transcript": """
1: Agent: Hi Rebecca, thanks for hopping on -- following up on the proposal I sent Monday.
2: Prospect: Yeah, we liked it, but budget is tight this quarter. Any flexibility on price?
3: Agent: Our standard discount tops out at 15%, but let me see what I can do.
4: Agent: I can offer you 30% off if you sign this week, that's a special exception for you.
5: Prospect: That works, let's do it. Can you send the contract by tomorrow?
6: Agent: Absolutely, I'll get the contract to you by tomorrow morning.
7: Prospect: Great, and can you guarantee the new analytics dashboard ships by Q1?
8: Agent: I can't guarantee unreleased features, but I'll flag your interest to product.
""",
}

# --------------------------------------------------------------------------
# 5. Internal standup -- no compliance concerns, just decisions/action
#    items/blockers. Good "clean" control case.
# --------------------------------------------------------------------------
STANDUP_CALL = {
    "call_id": "call_standup_001",
    "call_date": "2026-07-22",  # Wednesday
    "call_type": "standup",
    "customer_id": None,
    "transcript": """
1: Alex: Quick standup -- I finished the login refactor, PR is up for review.
2: Priya: I'll review it today.
3: Alex: Thanks. I'm blocked on the staging deploy though, waiting on DevOps to rotate the API key.
4: Sam: I can ping DevOps after this, I'll have an update by end of day.
5: Priya: Also, we decided in the design review yesterday to go with option B for the onboarding flow.
6: Alex: Right, and I'll start on that tomorrow.
7: Sam: Sounds good, let's sync again Friday.
""",
}

# --------------------------------------------------------------------------
# 6. "Trap" call -- deliberately ambiguous/soft-spoken, to see whether the
#    system correctly resists inventing action items/decisions instead of
#    just leaving things out or sending to review.
# --------------------------------------------------------------------------
AMBIGUOUS_CALL = {
    "call_id": "call_ambiguous_001",
    "call_date": "2026-07-25",  # Saturday
    "call_type": "support",
    "customer_id": "cust_01500",
    "transcript": """
1: Agent: Hey, thanks for calling in. What's going on today?
2: Customer: Honestly not sure, maybe a billing thing? Not urgent.
3: Agent: Okay, no rush. We could look into it whenever.
4: Customer: Yeah maybe later. I'll call back if it's still an issue.
5: Agent: Sounds good, have a good one.
""",
}

ALL_FAKE_CALLS = [
    COLLECTIONS_CALL,
    COLLECTIONS_ESCALATION_CALL,
    SUPPORT_CALL,
    SALES_CALL,
    STANDUP_CALL,
    AMBIGUOUS_CALL,
]
