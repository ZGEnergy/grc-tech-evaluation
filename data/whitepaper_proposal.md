# Grid Research Company LLC — Statement of Work
## Contract FA714626C0006 | Naval Research Laboratory

---

## 1.0 Introduction and Background

This Statement of Work (SOW) outlines the proposed research and development efforts to support the Naval Research Laboratory (NRL) in advancing grid modeling and simulation capabilities for the California electrical grid. The primary focus is on identifying vulnerabilities and pressure points at Camp Pendleton, Naval Base San Diego, and the Ports of Long Beach/Los Angeles. The effort emphasizes forecasting and identifying risks on key grid interconnects to support mission assurance and operational resilience. The project will leverage open-source tools, while incorporating minimal proprietary technologies as necessary.

This SOW is submitted as a proposal to the Naval Research Laboratory for funding and execution over 12 months.

---

## 2.0 Objectives

1. Evaluate and select an optimal technology stack for high-voltage transmission system modeling.
2. Produce a white paper sharing conclusions.
3. Develop a substation fidelity model of the California high-voltage transmission system that reflects actual outcomes at load and generator interconnection points.
4. Demonstrate model output quality by validating results against grid operator data.

---

## 3.0 Why This Work is Innovative

Current transmission-system studies rely heavily on proprietary tools that are costly, hard to extend, and difficult to validate. This limits the number of scenarios that can be explored and makes it difficult for government analysts to maintain a persistent, reusable modeling capability. The proposed effort is innovative because it creates a transparent, scalable, government-controlled modeling approach that does not exist today.

**1. A capability not yet implemented.**
Open-source grid tools exist, but no group has built or validated a substation-level model of the California transmission system that integrates long-term forecasting and site-specific vulnerability analysis. Likewise, no structured comparison of open-source and proprietary tools has been performed at this fidelity or scale.

**2. Novel use of existing technologies.**
Open tools are typically used for academic planning. Here, they are applied to operational risk analysis for specific defense-relevant locations and evaluated directly against commercial tools. This turns exploratory research into a practical, decision-support capability.

**3. Enabling previously impractical analysis.**
Proprietary licensing and opaque workflows constrain today's modeling efforts. By incorporating open-source components where feasible, the customer can scale scenario counts, expand geographic scope, and onboard additional analysts without proportionally increasing software costs.

**4. A different approach from current practice.**
Instead of commissioning isolated, vendor-specific studies, this work builds a government-owned modeling stack with standardized data ingestion, transparent algorithms, and reproducible workflows. This allows independent verification and continuity even as personnel, vendors, or mission priorities shift.

**5. New opportunities unlocked.**
A validated, substation-level modeling approach establishes a durable analytical engine that can be extended to new threats, regions, and missions. It also lays the groundwork for follow-on vulnerability assessments, stress testing, and integration with other critical-infrastructure models.

Overall, this effort moves grid modeling from occasional, vendor-constrained studies to a persistent, transparent, and scalable capability under government control.

---

## 4.0 Scope of Work

The scope is divided into two interconnected tasks aligned with the objectives. Task 1 focuses on technology evaluation and white paper production. Task 2 involves model development and quality demonstration. Follow-on scope expansions may include vulnerability analysis and graphical demonstrations. All work will prioritize open-source solutions for solvers and simulations, while evaluating proprietary options where they provide necessary functionality.

Models will incorporate long-term forecasting capabilities and be built to substation fidelity, ensuring they reflect real-world grid and market dynamics using publicly available data from sources like the California ISO and WECC. To allow for team ramp-up, initial tasks will emphasize planning and evaluation with a smaller core team, transitioning to full development as the team expands.

### Task 1: Technology Evaluation and White Paper

#### 1.1 Identify and Evaluate Modeling Technologies

- Conduct a comprehensive review of a targeted set of open-source and proprietary technologies capable of modeling the California high-voltage transmission system at substation fidelity.
- Evaluate tools for suitability in grid modeling, including support for long-term forecasting and vulnerability identification.

#### 1.2 Select Optimal Technology Stack

- Down-select to an initial tech stack based on evaluation results, with provisions for refinement as the team grows.

#### 1.3 Produce White Paper

- Develop a preliminary white paper summarizing key evaluation findings and initial recommendations.

### Task 2: Model Development and Demonstration

#### 2.1 Develop Substation CAISO Model

- Using the selected tech stack, construct an initial model of the California grid.
- Incorporate basic substation-level details and initial long-term forecasting elements.
- Perform preliminary validation against available real-world data.

#### 2.2 Demonstrate Output Quality

- Conduct simulations to showcase initial model outputs and accuracy.

---

## 5.0 Deliverables

| Deliverable | Description | Date | Task |
|-------------|-------------|------|------|
| Produce Technology Evaluation Report | Preliminary document sharing key conclusions on technology evaluation. | Month 4 | Task 1 |
| Develop Initial Grid Model Prototype | Basic substation fidelity model of the California grid, including key sites. | Month 10 | Task 2 |
| Validate Model and Produce Output Quality Report | Demonstration of model accuracy and outputs with statistical validation. | Month 12 | Task 2 |

---

## 6.0 Timeline and Milestones

This 12-month period focuses on technology evaluation, selection, and initial model development. During Task 1, there is flexibility in the team hiring phase.

- **Month 4:** Completion of Task 1 (evaluation, selection, white paper).
- **Month 12:** Completion of Task 2 (model development, output demonstration).

Progress will be tracked via monthly status reports and quarterly reviews, with flexibility for adjustments during the team hiring phase.

---

## 7.0 Assumptions and Constraints

- Simulation data will be limited by the data made available to CAISO market participants plus commercial sources.
- The compute resources required are poorly understood. We are not aware of any group that has completed this work at this fidelity and scale. GRC may demonstrate the need for government-provided compute clusters to complete the project.
- Security classifications: Work will be conducted at unclassified levels unless otherwise specified. GRC will transfer sensitive analysis through DoD approved channels, when appropriate.

---

## 8.0 Budget

- The initial estimate for Tasks 1 & 2 (12 months) is $1M.
- Hiring for the team will occur when there is clarity on the tech stack (Task 1). This will inform the depth of the roster needed for Task 2 and subsequent scope expansions.

---

## 9.0 Demographic Information

**Primary Point of Contact / Contract Manager**
Joe Shull
Email: joe@zerogcapital.com
Phone: 303-815-4080

**Backup Point of Contact**
Sasha Shtern
Email: sasha@zerogcapital.com
Phone: 303-835-3548

**Entity Information**
**Legal Entity:** Grid Research Company LLC (GRC), a wholly-owned subsidiary of ZG Energy LLC
**CAGE Code:** 15HL5
**Website:** www.zgenergy.co (GRC does not yet have a separate website)
**Physical Address:** 350 Interlocken Blvd, STE 380, Broomfield, CO 80021 (shared with ZG Energy)
