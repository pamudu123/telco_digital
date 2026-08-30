For the design document, the **first stage should be “POC Scope and Problem Definition.”** Before database schemas, Neo4j, ML models, or UI design, the document should clearly explain **what problem the POC is proving and what success looks like**.

I would structure Stage 1 like this:

1. **Problem Statement**
   Omobio has multiple digital applications such as Selfcare, Loyalty, adReach, Viber Campaign Manager, Mobile Money and SFA. These applications can generate useful customer and business data, but the POC explores how combining that information into a shared intelligence platform can enable cross application AI capabilities.

2. **POC Objective**
   Prove that customer and business events from multiple systems can be combined, relationships analysed, historical behaviour remembered, and AI/ML used to generate explainable recommendations, predictions and warnings.

3. **Core POC Capabilities**
   The POC should demonstrate:
   • Churn and behavioural intelligence
   • Next Best Action and personalised recommendations
   • Graph based fraud detection
   • Retailer demand forecasting and SFA recommendations
   • Customer and retailer Digital Twins
   • AI Copilot explanations

4. **Interactive Simulation Requirement**
   The evaluator can select predefined users, choose a date/time and generate actions such as travelling, recharging, purchasing a package, using data, making a payment, redeeming loyalty points or submitting a complaint.

   Every activity becomes part of that user's historical timeline.

5. **Adaptive Behaviour Requirement**
   Recommendations must consider:
   • Current customer state
   • Recent behaviour
   • Long term behaviour
   • Similar historical events
   • Similar customers where personal history is insufficient
   • Known versus unknown information
   • Graph relationships

6. **Example POC Scenario**
   User 1 travels to Singapore.

   ```text
   Travel Event
        ↓
   Historical behaviour retrieved
        ↓
   Previous Singapore/travel events analysed
        ↓
   Recent usage analysed
        ↓
   Digital Twin updated
        ↓
   Recommendation Engine
        ↓
   Suitable roaming options shown
   ```

   If trip duration is unknown, the system should not invent it. It could provide several options or request that missing information.

7. **Anomaly Scenario**
   If User 1 is recorded in Singapore at 9:00 AM and the USA at 10:00 AM:

   ```text
   New Event
       ↓
   Compare with existing timeline
       ↓
   Impossible travel detected
       ↓
   Warning generated
   ```

8. **POC Success Criteria**
   At the end of the demonstration, an evaluator should be able to create an event and visibly see:

   ```text
   Event
     ↓
   Historical Data
     ↓
   Relationship / Graph Context
     ↓
   Digital Twin Update
     ↓
   AI / ML Analysis
     ↓
   Prediction / Warning / Recommendation
     ↓
   Explanation
   ```

### Then Stage 2

Once **Stage 1: POC Scope and Problem Definition** is locked, I would move to:

> **Stage 2: Data and Information Architecture**

That is where we define the Excel dataset first, entities, event model, IDs, relationships, temporal history, how it later maps to Supabase/PostgreSQL, and what information eventually goes into Neo4j.

So I would **not start your design document with the database schema**. Start with **why the POC exists, what it proves, what the evaluator can do, and what outputs they should see**. Then the architecture becomes much easier to justify.
