# How to Use the New Workpaths (Phase 60)

The "Broken Pipes" have been fixed. Here is the new flow of information in Z-ORG.

## 1. The Central Intake (The_Bridge/Inbox)

You (the User) only need to drop files here. **AgentChiefOfStaff** watches this folder and routes files instantly.

* **Bills**: File name must start with `BILL`.
  * *Route*: `governance/proposals` (read by **AgentCongress**).
* **Strategy**: JSON type `STRATEGY` or `NEWS`.
  * *Route*: `The_Bridge/Pipelines/Strategy`.
* **Wealth**: JSON type `WEALTH` or `FINANCE`.
  * *Route*: `The_Bridge/Pipelines/Wealth` (read by **AgentStrategist**).
* **Education**: JSON type `EDUCATION` or `LESSON`.
  * *Route*: `The_Bridge/Pipelines/Education` (read by **AgentScholar**).

## 2. Direct Command Examples

### Force Buy (AgentStrategist)

Create `The_Bridge/Inbox/FORCE_BUY_ETH.json`:

```json
{
    "type": "WEALTH",
    "signal": "FORCE_BUY",
    "amount": 500,
    "reason": "User Override"
}
```

### Research Request (AgentScholar)

Create `The_Bridge/Inbox/RESEARCH_AGENTS.json`:

```json
{
    "type": "EDUCATION",
    "title": "Autonomous Agents",
    "content": "Research the latest frameworks for autonomy."
}
```

### New Law (AgentCongress)

Create `The_Bridge/Inbox/BILL-LEF-001.json`:

```json
{
    "id": "BILL-LEF-001",
    "type": "PROPOSAL",
    "title": "Test Bill",
    "description": "Testing the pipes.",
    "technical_spec": { "changes": [] }
}
```
