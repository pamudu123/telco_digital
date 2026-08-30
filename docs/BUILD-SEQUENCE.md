# Build sequence (locked)

Code in this exact order. The first implementation slice in this repository covers steps 01–33 (through impossible-travel proof). Later steps are scaffolded, not implemented.

## Sequence

01. Create repository  
02. Configure Python project  
03. Add Docker Compose  
04. Start PostgreSQL  
05. Start Neo4j  
06. Configure SQLAlchemy async engine  
07. Configure Alembic  
08. Create PostgreSQL schemas  
09. Create Customer  
10. Create Account  
11. Create Device  
12. Create Plan  
13. Create Subscription  
14. Create Balance Ledger  
15. Create Recharge  
16. Create Usage Event  
17. Create Travel  
18. Create Activity Event  
19. Create Outbox Event  
20. Write repositories  
21. Write UnitOfWork  
22. Write customer creation service  
23. Write recharge service  
24. Write plan purchase service  
25. Write data usage service  
26. Write travel service  
27. Write timeline query  
28. Write point-in-time CustomerStateService  
29. Write tests  
30. Seed U001–U005  
31. Test historical reconstruction  
32. Write warning rules  
33. Test impossible travel  
34. Build outbox worker  
35. Connect Neo4j  
36. Build GraphProjector  
37. Project Customer  
38. Project Device  
39. Project Wallet/Merchant  
40. Test graph rebuild  
41. Build TemporalFeatureService  
42. Build EventMemoryService  
43. Build travel episode extraction  
44. Build similar-event matching  
45. Build CustomerContext  
46. Build DigitalTwin V1  
47. Generate background population  
48. Train behaviour model  
49. Train churn model  
50. Build CandidateGenerator  
51. Build RecommendationService  
52. Add uncertainty handling  
53. Build fraud graph features  
54. Build fraud scorer  
55. Generate SFA dataset  
56. Build retailer forecast  
57. Build DecisionEngine  
58. Build explanation layer  
59. Build Copilot  
60. Add APIs  
61. Add UI  
62. Deploy PostgreSQL to Supabase  

Step 33 is the most important milestone. After that, Neo4j / ML / twins / recommendations are intelligence layers on a proven temporal core.

## Unit of Work (conceptual)

```
Application Service
       ↓
UnitOfWork
       ↓
PostgreSQL transaction
```

```python
async with unit_of_work:
    subscription = ...
    await subscription_repository.add(subscription)
    event = DomainEvent(...)
    await event_repository.add(event)
    await outbox_repository.add(event.to_outbox())
    await unit_of_work.commit()
```

Domain/application depend on repository abstractions (`CustomerRepository`, `PlanRepository`, `EventRepository`, `OutboxRepository`, …). PostgreSQL implementations live under `infrastructure`. Later Supabase does not require rewriting the domain.

## Logging (from the beginning)

Log `correlation_id`, `customer_id`, `command`, `event_id`, projection status, model version, decision id so one simulator action can be traced end to end.

## Seed customers (deterministic demo)

| Ref | Persona | Used for |
|---|---|---|
| U001 | Frequent traveller, heavy data | travel memory, recommendations |
| U002 | Price sensitive, frequent small recharge | behaviour, loyalty |
| U003 | High value, stable | control |
| U004 | Declining engagement, network problems | churn |
| U005 | Suspicious device/wallet relationships | graph fraud |

Then generate 1,000–5,000 background users from personas, not independent random values.
