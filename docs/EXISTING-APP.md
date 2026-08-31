Yes. I would connect the new **Unified Intelligence Platform features directly into the company's existing applications**, instead of positioning them as separate products.

The company's current digital service set in your source includes Mobile Selfcare, Mobile Sales Force Automation, Loyalty Management, Viber Campaign Manager, Mobile Money, Mobile Lottery and adReach.

# Feature → Existing Company Application

| New intelligence feature          | Selfcare | Loyalty | adReach | Viber | Mobile Money | SFA | Lottery |
| --------------------------------- | :------: | :-----: | :-----: | :---: | :----------: | :-: | :-----: |
| Customer 360                      |     ✅    |    ✅    |    ✅    |   ✅   |       ✅      |  △  |    △    |
| Behaviour intelligence            |     ✅    |    ✅    |    ✅    |   ✅   |       ✅      |  ✅  |    △    |
| Event Memory                      |     ✅    |    ✅    |    ✅    |   ✅   |       △      |  ✅  |    △    |
| Digital Twin                      |     ✅    |    ✅    |    ✅    |   ✅   |       ✅      |  ✅  |    △    |
| Churn prediction                  |     ✅    |    ✅    |    ✅    |   ✅   |              |     |         |
| Next Best Offer                   |     ✅    |    ✅    |    ✅    |   ✅   |              |     |         |
| Next Best Action                  |     ✅    |    ✅    |    ✅    |   ✅   |       ✅      |  ✅  |    △    |
| Uncertainty-aware recommendations |     ✅    |    ✅    |    ✅    |   ✅   |              |  ✅  |         |
| Graph intelligence                |     △    |    ✅    |    ✅    |   △   |       ✅      |  ✅  |    ✅    |
| Fraud detection                   |          |    ✅    |         |       |       ✅      |  ✅  |    ✅    |
| Campaign intelligence             |     ✅    |    ✅    |    ✅    |   ✅   |              |     |    △    |
| Demand forecasting                |          |         |         |       |              |  ✅  |         |
| Retailer intelligence             |          |         |         |       |              |  ✅  |         |
| Anomaly/warning engine            |     ✅    |    △    |         |       |       ✅      |  ✅  |    ✅    |
| AI Copilot                        |     ✅    |    ✅    |    ✅    |   ✅   |       ✅      |  ✅  |    △    |

`✅` strong direct use
`△` secondary or future use

---

# 1. Mobile Selfcare App

Selfcare is probably the **main customer-facing consumer** of the platform.

Your source already identifies personal telecom-agent functionality, prediction of customer problems and combining network information with customer information as opportunities for Selfcare. 

### Connect these features

**Customer 360**

Selfcare can understand:

```text
Current package
Data usage
Recharge behaviour
Loyalty balance
Network experience
Previous package choices
Previous travel
Campaign responses
```

### Behaviour Intelligence

Example:

```text
Heavy data user
+
Frequent traveller
+
Medium price sensitivity
```

Selfcare changes what it presents.

### Event Memory

Example:

> Last time this customer travelled to Singapore, they stayed six days, purchased 15 GB and consumed 11.4 GB.

This becomes historical evidence for the next recommendation.

### Digital Twin

Selfcare gets the current interpreted customer state:

```text
Observed
Current plan
Current location
Remaining data

Recent
Usage increasing

Historical
Previous Singapore trip

Inferred
Heavy data user

Predicted
Upgrade propensity = 82%

Unknown
Trip duration
```

### Next Best Offer

```text
Recommend:
ROAM_15
```

### Next Best Action

Sometimes:

```text
Offer package
```

Sometimes:

```text
Ask trip duration
```

Sometimes:

```text
Show 3 package options
```

Sometimes:

```text
Do nothing
```

### Uncertainty-aware recommendation

This is particularly important for Selfcare.

```text
Destination = Singapore
Trip duration = unknown
```

Instead of falsely recommending one package:

```text
1–3 days → ROAM_5
4–7 days → ROAM_15
8–14 days → ROAM_30
```

### Churn

If churn increases because of network problems:

```text
Selfcare
   ↓
Don't aggressively upsell
   ↓
Show support/compensation action
```

---

# 2. Loyalty Management

Your source already identifies behaviour analysis, identifying who buys because an offer is made, customer retention and churn intervention around Loyalty. 

This becomes much stronger with the shared platform.

### Behaviour Intelligence

Understand:

```text
Sports affinity
Streaming affinity
Travel behaviour
Price sensitivity
Promotion responsiveness
Reward preferences
```

### Personalised Reward Recommendation

Instead of:

> Give everyone 500 points.

Customer A:

```text
5 GB bonus
```

Customer B:

```text
Streaming reward
```

Customer C:

```text
Roaming discount
```

### Event Memory

Remember:

> This customer consistently chooses data rewards rather than merchant vouchers.

Next time:

```text
Data reward ranked higher
```

### Churn + Retention

```text
Churn risk = 76%
        +
High customer value
        +
Network problems
        ↓
Retention action
```

Possibly:

```text
Free 5 GB
+
Loyalty points
```

### Uplift modelling

Very useful here.

Determine:

> Who will change behaviour specifically because we offer the reward?

That avoids wasting loyalty benefits.

### Loyalty Fraud

Neo4j:

```text
Customer A ─┐
Customer B ─┼→ Device X
Customer C ─┘

All redeem
      ↓
Same merchant
```

Flag possible loyalty abuse.

---

# 3. adReach

adReach becomes one of the biggest beneficiaries of the intelligence platform.

Your material already describes contextual targeting such as airport/travel scenarios and event-driven data package promotion. 

### Customer Segmentation

Instead of only demographic segmentation:

```text
Frequent Traveller
High Data User
Sports Fan
Price Sensitive
Promotion Responsive
Potential Churner
```

### Next Best Offer

```text
Customer A → roaming
Customer B → data add-on
Customer C → loyalty
Customer D → nothing
```

### Campaign Propensity

Predict:

```text
Probability customer clicks
Probability customer converts
Probability customer purchases
```

### Uplift modelling

Target customers whose behaviour is likely to change **because of the campaign**.

### Real-time Context

Example:

```text
Airport event
      +
Previous travel behaviour
      +
No roaming package
      ↓
adReach
      ↓
Roaming campaign
```

### Campaign fatigue

Detect:

```text
12 campaigns
2 weeks
0 engagement
```

Decision:

```text
Stop contacting temporarily
```

This is where NBA can explicitly return:

> **DO_NOT_CONTACT**

---

# 4. Viber Campaign Manager

Your source already identifies generative campaign creation, automatic experimentation and send-time optimisation. 

### Audience Intelligence

Use the same customer segmentation from the shared platform.

### Personalised Content

The intelligence layer determines:

```text
Customer
Offer
Reason
Preferred language
Preferred channel/time
```

Then GenAI creates the message.

### Send Time Optimisation

Customer A:

```text
08:15
```

Customer B:

```text
19:30
```

### Campaign Experimentation

```text
Message A
Message B
Message C
```

Measure responses and feed them back into the platform.

### Next Best Channel

Sometimes Viber may not even be the best channel.

```text
Viber probability       0.32
Selfcare probability    0.78
```

Decision engine can choose Selfcare instead.

---

# 5. Mobile Money

This should primarily consume the **Graph Intelligence + Fraud Intelligence** capability.

Your source already identifies real-time transaction fraud detection and risk analysis for Mobile Money. 

### Transaction Risk

PostgreSQL features:

```text
Amount
Time
Frequency
Location
Device
Merchant
Historical transaction behaviour
```

### Neo4j Graph Risk

```text
Customer
   ↓
Device
   ↑
Another Customer
   ↓
Wallet
   ↓
Suspicious Merchant
```

### Combined Fraud Intelligence

```text
Transaction risk      0.42
Behaviour anomaly     0.68
Graph risk            0.94

       ↓

Overall risk = HIGH
```

### Merchant Digital Twin

```text
Normal transactions/day
Current transactions/day
Average transaction value
Customer concentration
Graph risk
Fraud probability
```

### Warning Engine

Instead of automatically saying:

> Fraud.

Return:

```text
HIGH RISK

Reasons:
Shared device
Unusual transaction velocity
2-hop connection to suspicious merchant

Recommended:
Step-up verification / review
```

---

# 6. Mobile Sales Force Automation

This is another major application.

Your source shows that SFA already deals with inventory, selling activity, retailer stock, targets, representative locations, routes, commissions, KPIs and customer requests. 

It also identifies demand forecasting and potential fraud/anomaly patterns such as unusual SIM registrations, impossible GPS movements, commission manipulation, duplicate retailers and suspicious sales spikes. 

### Retailer Digital Twin

For every retailer:

```text
Current inventory
Sales trend
Last visit
Promotion history
Expected demand
Stockout probability
Fraud risk
Growth potential
```

### Demand Forecasting

```text
Current SIM stock = 18
Predicted 7-day demand = 47

Stockout probability = 86%
```

### SFA Recommendation

```text
Visit tomorrow

Deliver:
40–50 SIMs

Promote:
Package A
```

### Sales Agent Prioritisation

```text
Retailer A
Stockout risk = 86%

Retailer B
Sales opportunity = 81%

Retailer C
Normal
```

Sales agent receives:

```text
Today's priority

1. Retailer A
2. Retailer B
```

### Behavioural Event Memory

This works for retailers too.

> Last time this retailer experienced similar sales growth, SIM inventory ran out within four days.

Therefore:

```text
Pre-emptive restocking recommended
```

### Graph Fraud

Neo4j can connect:

```text
Distributor
   ↓
Retailer
   ↓
Sales Agent
   ↓
SIM
   ↓
Customer
```

Useful for:

```text
SIM activation fraud
Commission fraud
Fake retailer networks
Inventory manipulation
```

---

# 7. Mobile Lottery

I would make Lottery a **secondary POC integration**, not one of the primary demonstrations.

Your source primarily identifies campaign forecasting and contextual campaign concepts around this part of the product set. 

Useful platform features include:

### Fraud/abuse detection

```text
Shared devices
Multiple accounts
Suspicious redemption
Coordinated activity
```

### Campaign forecasting

Predict participation levels and operational demand.

### Responsible monitoring

Identify abnormal engagement rather than using AI simply to maximise participation.

---

# 8. One Customer Intelligence Service, many applications

This is the most important architectural idea.

Don't build:

```text
Selfcare Churn Model

Loyalty Churn Model

adReach Churn Model

Viber Churn Model
```

Build:

```text
             CUSTOMER INTELLIGENCE
                     │
       ┌─────────────┼─────────────┐
       ↓             ↓             ↓
    Selfcare      Loyalty       adReach
                                    ↓
                                  Viber
```

Same for recommendations.

```text
            RECOMMENDATION ENGINE
                     │
       ┌─────────────┼─────────────┐
       ↓             ↓             ↓
    Selfcare      Loyalty       adReach
                                    ↓
                                  Viber
```

This is consistent with your original platform direction of having one intelligence layer rather than each system independently learning about the same customer. 

---

# 9. Graph Intelligence is also shared

Similarly:

```text
                NEO4J
                  │
           Graph Intelligence
                  │
       ┌──────────┼───────────┐
       ↓          ↓           ↓
 Mobile Money   Loyalty      SFA
                              │
                              ↓
                           Lottery
```

Different applications ask different questions of the same relationship graph.

### Mobile Money

> Are these accounts part of a fraud ring?

### Loyalty

> Are multiple accounts abusing one reward mechanism?

### SFA

> Are suspicious SIMs connected through the same retailer/agent?

### adReach

> Which behavioural communities exist?

---

# 10. Event Memory is shared too

```text
                  EVENT MEMORY
                       │
         ┌─────────────┼─────────────┐
         ↓             ↓             ↓
      Selfcare      Loyalty         SFA
         ↓             ↓             ↓
     Previous       Previous      Previous
      travel         reward        retailer
      events         choices       patterns
```

Examples:

**Selfcare**

> What happened last time this customer travelled?

**Loyalty**

> What rewards has this customer historically selected?

**SFA**

> What happened last time this retailer had similar demand?

---

# 11. Digital Twin connection

The source already describes the proposed customer digital representation around usage, spending, packages, device, network experience, location patterns, service interactions, loyalty, campaign response, payment behaviour, churn, fraud risk, price sensitivity and intent. 

I would extend this into multiple twins:

```text
Customer Twin
   │
   ├──── Selfcare
   ├──── Loyalty
   ├──── adReach
   ├──── Viber
   └──── Mobile Money


Retailer Twin
   │
   └──── SFA


Merchant Twin
   │
   └──── Mobile Money
```

Eventually:

```text
Network Twin
   │
   └──── Customer Twin
```

---

# 12. Final connection architecture

```text
                    EXISTING COMPANY APPLICATIONS

 Selfcare   Loyalty   adReach   Viber   Mobile Money   SFA   Lottery
     │         │         │        │          │          │       │
     └─────────┴─────────┴────────┴──────────┴──────────┴───────┘
                                │
                                ▼
                    POSTGRESQL DATA LAYER
                                │
                       Events + History
                                │
                   ┌────────────┴────────────┐
                   ▼                         ▼
          Temporal Intelligence            Neo4j
                   │                  Graph Intelligence
                   │                         │
                   └────────────┬────────────┘
                                ▼
                         EVENT MEMORY
                                │
                                ▼
                        DIGITAL TWINS
                                │
           ┌────────────────────┼────────────────────┐
           ▼                    ▼                    ▼
       Behaviour             Churn               Fraud
           │                    │                    │
           ├──────────── Recommendation ─────────────┤
           │                    │                    │
           │              Demand Forecast            │
           │                    │                    │
           └────────────────────┼────────────────────┘
                                ▼
                         DECISION ENGINE
                                │
               ┌────────────────┼────────────────┐
               ▼                ▼                ▼
          Recommendation      Warning       Next Best Action
               │                │                │
               └────────────────┼────────────────┘
                                ▼
                    EXISTING COMPANY APPLICATIONS
```

## For your POC, I would demonstrate these exact connections

| Demo                                              | AI capability                                     | Existing company application           |
| ------------------------------------------------- | ------------------------------------------------- | -------------------------------------- |
| **User 1 travels to Singapore**                   | Event Memory + uncertainty-aware recommendation   | **Mobile Selfcare**                    |
| **User 2 repeatedly makes small recharges**       | Behaviour intelligence + personalised reward/plan | **Selfcare + Loyalty**                 |
| **User 4 usage falls and complaints rise**        | Churn + Next Best Action                          | **Selfcare + Loyalty + adReach/Viber** |
| **User 5 shares device with suspicious accounts** | Neo4j graph fraud                                 | **Mobile Money**                       |
| **Retailer stock falls while demand rises**       | Forecast + retailer twin + recommendation         | **Mobile SFA**                         |
| **Campaign response history changes**             | Campaign intelligence                             | **adReach + Viber**                    |

That gives you a very clear story: **we are not creating new applications to compete with the company's existing products. We are creating a shared AI intelligence layer that makes the existing company products smarter.** 
