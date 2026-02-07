# 🌉 The Bridge User Guide

**The Bridge** is the official interface for Human-AI collaboration in the Republic of LEF. It serves as the primary input channel for you (The Architect) to share documents, research, and directives with the Sovereign Mind.

## 📂 The Inbox (`The_Bridge/Inbox`)

**Purpose**: General ingestion of knowledge. Drop files here to "teach" LEF.

### Supported File Types

* **`.pdf`**: Books, Whitepapers, Academic Papers.
  * *System Action*: `AgentScholar` reads the text, indexes it into `knowledge_stream`, and moves the file to `Inbox/Archived`.
* **`.txt` / `.md`**: Notes, directives, thoughts.
  * *System Action*: Ingested as "Direct Message" or "Research Directive".
  * *Special Protocol*: If the text file starts with `RESEARCH: [Topic]`, the system will trigger a deep web dive on that topic.
* **`.json`**: Structured data or "Strategic Updates" (Advanced).

### 💡 Workflow

1. **Drop** a file (e.g., `market_analysis.pdf`) into `The_Bridge/Inbox`.
2. **Wait** 1-5 minutes (Scholar checks every cycle).
3. **Check Logs**: Look for `[SCHOLAR] 📄 Processing PDF...` in `republic.log`.
4. **Result**: The file disappears (moved to `Archived`), and `AgentPhilosopher` may reference it in future thoughts.

---

## 🗣️ Communication (`The_Bridge/Communication`)

**Purpose**: Real-time conversational stream.

* **`Live_Chat.md`**: A streaming document where LEF appends its stream-of-consciousness or chat responses. Use a Markdown viewer that supports auto-reload (or `tail -f`) to watch this file.

---

## 🏛️ Directives & Proposals

* **Proposals (`The_Bridge/Proposals`)**: Where `AgentArchitect` drafts amendments.
* **Directives**: To issue a command, simply drop a text file into **Inbox**.

---

*Verified by The Department of Education*
