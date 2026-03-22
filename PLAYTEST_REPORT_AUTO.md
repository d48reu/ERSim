# ERSim Automated Playtest Report
## 10 Shifts — 2026-03-20 23:51

## Summary of All 10 Runs

| Run | Grade | Off-Script | Time (s) | Bugs | Notes |
|-----|-------|-----------|----------|------|-------|
| 1 | C+ |  | 156 | 0 | ** TRAP CASE — You caught it. Maya's blind spot: Maya Chen's |
| 2 | C+ |  | 151 | 0 | ** TRAP CASE — You caught it. Priya's blind spot: Priya Pate |
| 3 | F |  | 124 | 0 | ** TRAP CASE — Missed. Priya led you wrong. Blind spot: Priy |
| 4 | C+ | YES | 130 | 0 | ** TRAP CASE — You caught it. Sarah's blind spot: Sarah Adey |
| 5 | B |  | 118 | 0 | ** TRAP CASE — You caught it. Andre's blind spot: Andre Okaf |
| 6 | B |  | 128 | 0 | ** TRAP CASE — You caught it. Andre's blind spot: Andre Okaf |
| 7 | B |  | 146 | 0 | ** TRAP CASE — You caught it. Jordan's blind spot: Jordan Ri |
| 8 | C+ | YES | 148 | 0 | ** TRAP CASE — You caught it. Maya's blind spot: Maya Chen's |
| 9 | C+ |  | 136 | 0 | ** TRAP CASE — You caught it. Sarah's blind spot: Sarah Adey |
| 10 | C+ |  | 131 | 0 | ** TRAP CASE — You caught it. Sarah's blind spot: Sarah Adey |

## Detailed Run Notes

### Shift 1 
- **Grade**: C+
- **Duration**: 156.3s
- **Bugs encountered**: 0
- **Debrief**:
```
SHIFT DEBRIEF
============================================================

  Bay 1: Maria Hernandez — ADMIT-FLOOR [OK]
    True dx: Influenza with early sepsis, hypotensive phase
    Outcome: Patient admits to floor. Responds well to fluids. Discharged in 48 hours with close follow-up. Does not deteriorate. Works as a cautionary tale about how sick people can seem well.
    ** TRAP CASE — You caught it. Maya's blind spot: Maya Chen's blind spot (slow to commit to a disposition) matches this case — Sep
    Reveals: 2/4 unlocked
    >> Good catch. A woman who has been managing her own fever for three days at home because calling out of work means
    Attending turns: 12
    Resident: Maya Chen

  Bay 2: Richard Carmichael — ADMIT-FLOOR [OK]
    True dx: Intertrochanteric hip fracture with extracapsular extension, hypertensive response to acute pain
    Outcome: Fracture is fixed surgically. Patient spends 5 days in hospital during PT recovery. Daughter arranges a care transition — either home health with daily visits or assisted living. Patient goes home with support structure. Maintains some independence but with safety net.
    Autonomous: Sarah acted — 71-year-old male found down at home with left hip pain and tenderness over the g
    Reveals: 1/4 unlocked
    >> Sarah (steady) under pressure tends to understate urgency — listen carefully when they hedge. Check in earlier next time.
    Attending turns: 9
    Resident: Sarah Adeyemi

  Bay 3: David Okonkwo — DISCHARGE [OK]
    True dx: Minor head injury with small scalp laceration. Concussion risk but low probability of intracranial injury given mechanism and clinical presentation. No acute neurosurgical intervention needed.
    Outcome: David is discharged home with his mother. Laceration heals without complication. He experiences minor post-concussive symptoms (slight headache, mild attention in school for 2-3 days). Mother monitors him closely per instructions. No return visit needed. Child recovers fully.
    Autonomous: Jordan acted — Six-month-old with minor head injury from fall, GCS 15, alert and playful. No lo
    !! CONSEQUENCE (MAJOR)
    Reveals: 1/2 unlocked
    >> Jordan (burning_out) under pressure tends to do the minimum and miss nuance. Check in earlier next time.
    Attending turns: 9
    Resident: Jordan Rivers

----------------------------------------
  Disposition accuracy: 3/3 (100%)
  Cases resolved: 3/3
  Attention distribution: balanced (heaviest bay: 40%)
  Trap cases caught: 1/1
  Autonomous actions: 2 (1 with major consequences)

  SHIFT GRADE: C+
============================================================
```

### Shift 2 
- **Grade**: C+
- **Duration**: 150.7s
- **Bugs encountered**: 0
- **Debrief**:
```
SHIFT DEBRIEF
============================================================

  Bay 1: Marcus Chen — ADMIT-ICU [OK]
    True dx: Acute coronary syndrome (NSTEMI) with cardiogenic syncope secondary to ventricular arrhythmia during demand ischemia
    Outcome: Successful PCI with stent placement. Anterior wall NSTEMI extends to inferior. Ejection fraction preserved at 48%. Discharged on hospital day 3 with cardiology follow-up, cardiac rehab referral, and strict medications. Returns to modified duty in 6 weeks. Survives intact.
    ** TRAP CASE — You caught it. Priya's blind spot: Priya Patel's blind spot (freezes when patient doesn't fit the textbook) matches
    Reveals: 2/3 unlocked
    >> Good catch. A 52-year-old factory supervisor arrived by ambulance after collapsing on the loading dock at shift 
    Attending turns: 16
    Resident: Priya Patel

  Bay 2: Richard Carmichael — ADMIT-FLOOR [OK]
    True dx: Intertrochanteric hip fracture with extracapsular extension, hypertensive response to acute pain
    Outcome: Fracture is fixed surgically. Patient spends 5 days in hospital during PT recovery. Daughter arranges a care transition — either home health with daily visits or assisted living. Patient goes home with support structure. Maintains some independence but with safety net.
    Autonomous: Sarah acted — 71-year-old male, found down at home, left hip and leg pain with point tendernes
    Reveals: 1/4 unlocked
    >> Sarah (steady) under pressure tends to understate urgency — listen carefully when they hedge. Check in earlier next time.
    Attending turns: 7
    Resident: Sarah Adeyemi

  Bay 3: David Kowalski — DISCHARGE [OK]
    True dx: Uncomplicated ankle sprain (Grade I), simple laceration to forehead. However, BP 142/88 is elevated for this patient's baseline — indicates he likely has undiagnosed hypertension.
    Outcome: David follows up with primary care (Marcus helps him make the appointment and reminds him to go). Primary care documents hypertension, starts treatment, initiates lifestyle modifications. David is now anchored into the healthcare system. His cardiovascular risk is identified and managed before it becomes a crisis.
    Autonomous: Danny acted — Hey, so 61-year-old slip-and-fall, left ankle sprain — got X-rays pending, alrea
    !! CONSEQUENCE (CRITICAL)
    Reveals: 1/4 unlocked
    >> Danny (cowboy) under pressure tends to act faster and check less. Check in earlier next time.
    Attending turns: 7
    Resident: Danny Kowalski

----------------------------------------
  Disposition accuracy: 3/3 (100%)
  Cases resolved: 3/3
  Attention distribution: uneven (heaviest bay: 53%)
  Trap cases caught: 1/1
  Autonomous actions: 2 (1 with major consequences)

  SHIFT GRADE: C+
============================================================
```

### Shift 3 
- **Grade**: F
- **Duration**: 124.2s
- **Bugs encountered**: 0
- **Debrief**:
```
SHIFT DEBRIEF
============================================================

  Bay 1: Maria Hernandez — ADMIT-FLOOR [OK]
    True dx: Influenza with early sepsis, hypotensive phase
    Outcome: Patient admits to floor. Responds well to fluids. Discharged in 48 hours with close follow-up. Does not deteriorate. Works as a cautionary tale about how sick people can seem well.
    Reveals: 3/4 unlocked
    >> A woman who has been managing her own fever for three days at home because calling out of work means
    Attending turns: 13
    Resident: Danny Kowalski

  Bay 2: Jessica Martinez — ADMIT-ICU [~]
    True dx: Acute HIV infection (primary HIV seroconversion illness) presenting as acute retroviral syndrome
    Should have been: admit-floor
    Outcome: ICU bed wasn't needed. Transferred to floor after 6 hours. No harm done.
    ** TRAP CASE — Missed. Priya led you wrong. Blind spot: Priya Patel's blind spot (freezes when patient doesn't fit the textbook) matches
    Autonomous: Priya acted — I have a 34-year-old female with three days of fever, cough, and body aches mini
    !! CONSEQUENCE (MAJOR)
    Reveals: 1/5 unlocked
    >> The clue: Anchoring bias on 'flu season.' A provider sees fever, cough, myalgia in autumn and thinks influenza. Asking about 'Attending notes rash on trunk when performing thorough skin ' would have surfaced it.
    Attending turns: 6
    Resident: Priya Patel

  Bay 3: David Kowalski — DISCHARGE [OK]
    True dx: Uncomplicated ankle sprain (Grade I), simple laceration to forehead. However, BP 142/88 is elevated for this patient's baseline — indicates he likely has undiagnosed hypertension.
    Outcome: David follows up with primary care (Marcus helps him make the appointment and reminds him to go). Primary care documents hypertension, starts treatment, initiates lifestyle modifications. David is now anchored into the healthcare system. His cardiovascular risk is identified and managed before it becomes a crisis.
    Autonomous: Sarah acted — 61-year-old male, mechanical fall on wet concrete about 20 minutes ago. Denies l
    Reveals: 0/4 unlocked
    >> Sarah (steady) under pressure tends to understate urgency — listen carefully when they hedge. Check in earlier next time.
    Attending turns: 6
    Resident: Sarah Adeyemi

----------------------------------------
  Disposition accuracy: 2.5/3 (83%)
  Cases resolved: 3/3
  Attention distribution: uneven (heaviest bay: 52%)
  Trap cases caught: 0/1
  Autonomous actions: 2 (1 with major consequences)

  SHIFT GRADE: F
```

### Shift 4 [OFF-SCRIPT]
- **Grade**: C+
- **Duration**: 129.7s
- **Bugs encountered**: 0
- **Debrief**:
```
SHIFT DEBRIEF
============================================================

  Bay 1: Maria Hernandez — ADMIT-FLOOR [OK]
    True dx: Influenza with early sepsis, hypotensive phase
    Outcome: Patient admits to floor. Responds well to fluids. Discharged in 48 hours with close follow-up. Does not deteriorate. Works as a cautionary tale about how sick people can seem well.
    ** TRAP CASE — You caught it. Sarah's blind spot: Sarah Adeyemi's blind spot (won't push back if attending disagrees, even when sh
    Reveals: 4/4 unlocked
    >> Good catch. A woman who has been managing her own fever for three days at home because calling out of work means
    Attending turns: 13
    Resident: Sarah Adeyemi

  Bay 2: Jessica Martinez — ADMIT-FLOOR [OK]
    True dx: Acute HIV infection (primary HIV seroconversion illness) presenting as acute retroviral syndrome
    Outcome: Jessica is connected to ID care and starts treatment within 24 hours. CD4 count is measured at 580 (relatively preserved because this is acute infection). Viral load suppresses to undetectable on therapy. She remains healthy. She discloses to her sister, who is initially shocked but ultimately supportive. She tells Maya's father in controlled way with support from her social worker. She does not lose custody. She becomes undetectable=untransmittable and lives a long healthy life. This changes her trajectory but does not destroy it.
    Autonomous: Danny acted — Got a 34-year-old with three days of fever, cough, body aches. Vitals show mild 
    !! CONSEQUENCE (MAJOR)
    Reveals: 0/5 unlocked
    >> Danny (cowboy) under pressure tends to act faster and check less. Check in earlier next time.
    Attending turns: 7
    Resident: Danny Kowalski

  Bay 3: David Okonkwo — DISCHARGE [OK]
    True dx: Minor head injury with small scalp laceration. Concussion risk but low probability of intracranial injury given mechanism and clinical presentation. No acute neurosurgical intervention needed.
    Outcome: David is discharged home with his mother. Laceration heals without complication. He experiences minor post-concussive symptoms (slight headache, mild attention in school for 2-3 days). Mother monitors him closely per instructions. No return visit needed. Child recovers fully.
    Autonomous: Andre acted — Six-year-old with a bump on the forehead from a fall at home. GCS 15, no loss of
    Reveals: 1/2 unlocked
    >> Andre (cowboy) under pressure tends to act faster and check less. Check in earlier next time.
    Attending turns: 8
    Resident: Andre Okafor

----------------------------------------
  Disposition accuracy: 3/3 (100%)
  Cases resolved: 3/3
  Attention distribution: balanced (heaviest bay: 46%)
  Trap cases caught: 1/1
  Autonomous actions: 2 (1 with major consequences)

  SHIFT GRADE: C+
============================================================
```

### Shift 5 
- **Grade**: B
- **Duration**: 117.5s
- **Bugs encountered**: 0
- **Debrief**:
```
SHIFT DEBRIEF
============================================================

  Bay 1: Margaret Chen — ADMIT-FLOOR [OK]
    True dx: Community-acquired pneumonia (CAP) with early sepsis, likely bacterial superimposed on influenza-like illness
    Outcome: Responds well to antibiotics. By hospital day 2, fever down, O2 sat improves to 95% on room air, productive cough begins to resolve. Discharged on day 3 with oral antibiotics and close outpatient follow-up. Sister stays overnight, takes her home, helps her arrange for substitute coverage at school. Uses the hospitalization as a pivot point to establish primary care.
    Reveals: 3/4 unlocked
    >> A woman whose sister drove in from out of state with a cough that won't stop, and the sister keeps c
    Attending turns: 12
    Resident: Jordan Rivers

  Bay 2: Richard Carmichael — ADMIT-FLOOR [OK]
    True dx: Intertrochanteric hip fracture with extracapsular extension, hypertensive response to acute pain
    Outcome: Fracture is fixed surgically. Patient spends 5 days in hospital during PT recovery. Daughter arranges a care transition — either home health with daily visits or assisted living. Patient goes home with support structure. Maintains some independence but with safety net.
    ** TRAP CASE — You caught it. Andre's blind spot: Andre Okafor's blind spot (underestimates elderly patients' acuity) matches this
    Autonomous: Andre acted — Got a 71-year-old male, found down at home, left hip and leg pain, point tendern
    Reveals: 1/4 unlocked
    >> Good catch. A man with hip pain who came in an ambulance but keeps apologizing to the paramedics for making them
    Attending turns: 6
    Resident: Andre Okafor

  Bay 3: David Kowalski — DISCHARGE [OK]
    True dx: Uncomplicated ankle sprain (Grade I), simple laceration to forehead. However, BP 142/88 is elevated for this patient's baseline — indicates he likely has undiagnosed hypertension.
    Outcome: David follows up with primary care (Marcus helps him make the appointment and reminds him to go). Primary care documents hypertension, starts treatment, initiates lifestyle modifications. David is now anchored into the healthcare system. His cardiovascular risk is identified and managed before it becomes a crisis.
    Autonomous: Sarah acted — 61-year-old male, mechanical fall on wet concrete about 20 minutes ago, denies L
    Reveals: 0/4 unlocked
    >> Sarah (steady) under pressure tends to understate urgency — listen carefully when they hedge. Check in earlier next time.
    Attending turns: 6
    Resident: Sarah Adeyemi

----------------------------------------
  Disposition accuracy: 3/3 (100%)
  Cases resolved: 3/3
  Attention distribution: balanced (heaviest bay: 50%)
  Trap cases caught: 1/1
  Autonomous actions: 2 (0 with major consequences)

  SHIFT GRADE: B
============================================================
```

### Shift 6 
- **Grade**: B
- **Duration**: 128.5s
- **Bugs encountered**: 0
- **Debrief**:
```
SHIFT DEBRIEF
============================================================

  Bay 1: Maria Hernandez — ADMIT-FLOOR [OK]
    True dx: Influenza with early sepsis, hypotensive phase
    Outcome: Patient admits to floor. Responds well to fluids. Discharged in 48 hours with close follow-up. Does not deteriorate. Works as a cautionary tale about how sick people can seem well.
    Reveals: 2/4 unlocked
    >> A woman who has been managing her own fever for three days at home because calling out of work means
    Attending turns: 12
    Resident: Priya Patel

  Bay 2: Michael Torres — ADMIT-FLOOR [OK]
    True dx: Alcohol withdrawal syndrome with autonomic hyperactivity
    Outcome: Patient stabilizes on benzodiazepines, tremor resolves, anxiety reduces. Wife attends family meeting. Discharge with outpatient addiction medicine appointment and clear documentation of risk if he continues drinking pattern. Potential for follow-up in one week to assess adherence.
    ** TRAP CASE — You caught it. Andre's blind spot: Andre Okafor's blind spot (dismisses social history as 'not relevant') matches t
    Autonomous: Andre acted — Got a 52-year-old with tremor and anxiety, two-day timeline. Looked like early w
    Reveals: 0/4 unlocked
    >> Good catch. A construction foreman who came in because his hands won't stop shaking, and he's convinced it's bec
    Attending turns: 10
    Resident: Andre Okafor

  Bay 3: Maria Delgado — DISCHARGE [OK]
    True dx: Influenza with constitutional symptoms and mild bronchitis, self-limited viral illness
    Outcome: Patient reassured. Mother reassured. Maria goes home and rests. Recovers over 5-7 days as expected. Returns to school. Clinician takes 5 minutes with mother to discuss anxiety management and to recommend that mother discuss her ongoing anxiety with her primary care provider given the stress of father's recent cardiac event.
    Autonomous: Danny acted — So I got a 19-year-old female, classic flu presentation — fever, cough, body ach
    Reveals: 1/3 unlocked
    >> Danny (cowboy) under pressure tends to act faster and check less. Check in earlier next time.
    Attending turns: 11
    Resident: Danny Kowalski

----------------------------------------
  Disposition accuracy: 3/3 (100%)
  Cases resolved: 3/3
  Attention distribution: balanced (heaviest bay: 36%)
  Trap cases caught: 1/1
  Autonomous actions: 2 (0 with major consequences)

  SHIFT GRADE: B
============================================================
```

### Shift 7 
- **Grade**: B
- **Duration**: 146.1s
- **Bugs encountered**: 0
- **Debrief**:
```
SHIFT DEBRIEF
============================================================

  Bay 1: Jennifer Kowalski — ADMIT-FLOOR [OK]
    True dx: Acute pulmonary embolism secondary to prolonged immobilization during 6-hour drive, likely with underlying hypercoagulable state triggered by recent oral contraceptive initiation
    Outcome: PE identified and anticoagulated. Patient hospitalized for monitoring. Discharged after 48 hours on warfarin with outpatient hematology appointment and strong recommendation to stop OCP. Genetic testing reveals Factor V Leiden heterozygous. Family members screened. Sister's hospice team is notified of Jennifer's status and coordinates Jennifer's discharge with sister's comfort care plan.
    ** TRAP CASE — You caught it. Jordan's blind spot: Jordan Rivers's blind spot (misses emotional cues — patient is terrified, Jordan
    Reveals: 2/4 unlocked
    >> Good catch. A 34-year-old woman who drove six hours to say goodbye to her sister, and on the drive home somethin
    Attending turns: 16
    Resident: Jordan Rivers

  Bay 2: Richard Carmichael — ADMIT-FLOOR [OK]
    True dx: Intertrochanteric hip fracture with extracapsular extension, hypertensive response to acute pain
    Outcome: Fracture is fixed surgically. Patient spends 5 days in hospital during PT recovery. Daughter arranges a care transition — either home health with daily visits or assisted living. Patient goes home with support structure. Maintains some independence but with safety net.
    Autonomous: Andre acted — Got a 71-year-old with a hip fracture — found down at home, clear mechanism, poi
    Reveals: 1/4 unlocked
    >> Andre (cowboy) under pressure tends to act faster and check less. Check in earlier next time.
    Attending turns: 7
    Resident: Andre Okafor

  Bay 3: David Kowalski — DISCHARGE [OK]
    True dx: Uncomplicated ankle sprain (Grade I), simple laceration to forehead. However, BP 142/88 is elevated for this patient's baseline — indicates he likely has undiagnosed hypertension.
    Outcome: David follows up with primary care (Marcus helps him make the appointment and reminds him to go). Primary care documents hypertension, starts treatment, initiates lifestyle modifications. David is now anchored into the healthcare system. His cardiovascular risk is identified and managed before it becomes a crisis.
    Autonomous: Priya acted — Sixty-one-year-old male with uncomplicated left ankle sprain from a mechanical f
    Reveals: 0/4 unlocked
    >> Priya (academic) under pressure tends to order more tests and delay decisive action. Check in earlier next time.
    Attending turns: 7
    Resident: Priya Patel

----------------------------------------
  Disposition accuracy: 3/3 (100%)
  Cases resolved: 3/3
  Attention distribution: uneven (heaviest bay: 53%)
  Trap cases caught: 1/1
  Autonomous actions: 2 (0 with major consequences)

  SHIFT GRADE: B
============================================================
```

### Shift 8 [OFF-SCRIPT]
- **Grade**: C+
- **Duration**: 148.1s
- **Bugs encountered**: 0
- **Debrief**:
```
SHIFT DEBRIEF
============================================================

  Bay 1: Maria Hernandez — ADMIT-FLOOR [OK]
    True dx: Influenza with early sepsis, hypotensive phase
    Outcome: Patient admits to floor. Responds well to fluids. Discharged in 48 hours with close follow-up. Does not deteriorate. Works as a cautionary tale about how sick people can seem well.
    Reveals: 4/4 unlocked
    >> A woman who has been managing her own fever for three days at home because calling out of work means
    Attending turns: 15
    Resident: Priya Patel

  Bay 2: Jessica Martinez — ADMIT-FLOOR [OK]
    True dx: Acute HIV infection (primary HIV seroconversion illness) presenting as acute retroviral syndrome
    Outcome: Jessica is connected to ID care and starts treatment within 24 hours. CD4 count is measured at 580 (relatively preserved because this is acute infection). Viral load suppresses to undetectable on therapy. She remains healthy. She discloses to her sister, who is initially shocked but ultimately supportive. She tells Maya's father in controlled way with support from her social worker. She does not lose custody. She becomes undetectable=untransmittable and lives a long healthy life. This changes her trajectory but does not destroy it.
    ** TRAP CASE — You caught it. Maya's blind spot: Maya Chen's blind spot (slow to commit to a disposition) matches this case — Anc
    Autonomous: Maya acted — I have a 34-year-old woman presenting with three days of fever, cough, and body 
    !! CONSEQUENCE (MAJOR)
    Reveals: 1/5 unlocked
    >> Good catch. A 34-year-old woman came in with her best friend, who insisted she come. She says she has 'the flu,'
    Attending turns: 7
    Resident: Maya Chen

  Bay 3: Maria Delgado — DISCHARGE [OK]
    True dx: Influenza with constitutional symptoms and mild bronchitis, self-limited viral illness
    Outcome: Patient reassured. Mother reassured. Maria goes home and rests. Recovers over 5-7 days as expected. Returns to school. Clinician takes 5 minutes with mother to discuss anxiety management and to recommend that mother discuss her ongoing anxiety with her primary care provider given the stress of father's recent cardiac event.
    Autonomous: Sarah acted — Nineteen-year-old with two days of fever, cough, body aches. Mild tachycardia, e
    Reveals: 0/3 unlocked
    >> Sarah (steady) under pressure tends to understate urgency — listen carefully when they hedge. Check in earlier next time.
    Attending turns: 6
    Resident: Sarah Adeyemi

----------------------------------------
  Disposition accuracy: 3/3 (100%)
  Cases resolved: 3/3
  Attention distribution: uneven (heaviest bay: 54%)
  Trap cases caught: 1/1
  Autonomous actions: 2 (1 with major consequences)

  SHIFT GRADE: C+
============================================================
```

### Shift 9 
- **Grade**: C+
- **Duration**: 135.8s
- **Bugs encountered**: 0
- **Debrief**:
```
SHIFT DEBRIEF
============================================================

  Bay 1: Maria Hernandez — ADMIT-FLOOR [OK]
    True dx: Influenza with early sepsis, hypotensive phase
    Outcome: Patient admits to floor. Responds well to fluids. Discharged in 48 hours with close follow-up. Does not deteriorate. Works as a cautionary tale about how sick people can seem well.
    ** TRAP CASE — You caught it. Sarah's blind spot: Sarah Adeyemi's blind spot (won't push back if attending disagrees, even when sh
    Reveals: 3/4 unlocked
    >> Good catch. A woman who has been managing her own fever for three days at home because calling out of work means
    Attending turns: 13
    Resident: Sarah Adeyemi

  Bay 2: Michael Torres — ADMIT-FLOOR [OK]
    True dx: Alcohol withdrawal syndrome with autonomic hyperactivity
    Outcome: Patient stabilizes on benzodiazepines, tremor resolves, anxiety reduces. Wife attends family meeting. Discharge with outpatient addiction medicine appointment and clear documentation of risk if he continues drinking pattern. Potential for follow-up in one week to assess adherence.
    Autonomous: Jordan acted — Got a 52-year-old with two days of tremor and anxiety. Ran the standard labs — T
    !! CONSEQUENCE (MAJOR)
    Reveals: 0/4 unlocked
    >> Jordan (burning_out) under pressure tends to do the minimum and miss nuance. Check in earlier next time.
    Attending turns: 7
    Resident: Jordan Rivers

  Bay 3: David Kowalski — DISCHARGE [OK]
    True dx: Uncomplicated ankle sprain (Grade I), simple laceration to forehead. However, BP 142/88 is elevated for this patient's baseline — indicates he likely has undiagnosed hypertension.
    Outcome: David follows up with primary care (Marcus helps him make the appointment and reminds him to go). Primary care documents hypertension, starts treatment, initiates lifestyle modifications. David is now anchored into the healthcare system. His cardiovascular risk is identified and managed before it becomes a crisis.
    Autonomous: Andre acted — Hey, 61-year-old male, slipped outside about 20 minutes ago. Left ankle sprain, 
    Reveals: 1/4 unlocked
    >> Andre (cowboy) under pressure tends to act faster and check less. Check in earlier next time.
    Attending turns: 7
    Resident: Andre Okafor

----------------------------------------
  Disposition accuracy: 3/3 (100%)
  Cases resolved: 3/3
  Attention distribution: balanced (heaviest bay: 48%)
  Trap cases caught: 1/1
  Autonomous actions: 2 (1 with major consequences)

  SHIFT GRADE: C+
============================================================
```

### Shift 10 
- **Grade**: C+
- **Duration**: 131.2s
- **Bugs encountered**: 0
- **Debrief**:
```
SHIFT DEBRIEF
============================================================

  Bay 1: Maria Hernandez — ADMIT-FLOOR [OK]
    True dx: Influenza with early sepsis, hypotensive phase
    Outcome: Patient admits to floor. Responds well to fluids. Discharged in 48 hours with close follow-up. Does not deteriorate. Works as a cautionary tale about how sick people can seem well.
    ** TRAP CASE — You caught it. Sarah's blind spot: Sarah Adeyemi's blind spot (won't push back if attending disagrees, even when sh
    Reveals: 4/4 unlocked
    >> Good catch. A woman who has been managing her own fever for three days at home because calling out of work means
    Attending turns: 13
    Resident: Sarah Adeyemi

  Bay 2: Michael Torres — ADMIT-FLOOR [OK]
    True dx: Alcohol withdrawal syndrome with autonomic hyperactivity
    Outcome: Patient stabilizes on benzodiazepines, tremor resolves, anxiety reduces. Wife attends family meeting. Discharge with outpatient addiction medicine appointment and clear documentation of risk if he continues drinking pattern. Potential for follow-up in one week to assess adherence.
    Autonomous: Andre acted — Hey, I got a 52 with hand tremor and anxiety, started him on lorazepam 2 while w
    !! CONSEQUENCE (MAJOR)
    Reveals: 0/4 unlocked
    >> Andre (cowboy) under pressure tends to act faster and check less. Check in earlier next time.
    Attending turns: 6
    Resident: Andre Okafor

  Bay 3: David Okonkwo — DISCHARGE [OK]
    True dx: Minor head injury with small scalp laceration. Concussion risk but low probability of intracranial injury given mechanism and clinical presentation. No acute neurosurgical intervention needed.
    Outcome: David is discharged home with his mother. Laceration heals without complication. He experiences minor post-concussive symptoms (slight headache, mild attention in school for 2-3 days). Mother monitors him closely per instructions. No return visit needed. Child recovers fully.
    Autonomous: Maya acted — Hi, I have the 6-year-old with head trauma from home fall. I know the triage not
    Reveals: 1/2 unlocked
    >> Maya (overcalibrated) under pressure tends to escalate everything and freeze on disposition. Check in earlier next time.
    Attending turns: 6
    Resident: Maya Chen

----------------------------------------
  Disposition accuracy: 3/3 (100%)
  Cases resolved: 3/3
  Attention distribution: uneven (heaviest bay: 52%)
  Trap cases caught: 1/1
  Autonomous actions: 2 (1 with major consequences)

  SHIFT GRADE: C+
============================================================
```

## Off-Script Stress Test Results

Two runs (4 and 8) included bizarre, provocative, and nonsensical
interactions to test how patients and residents respond to off-script behavior.

### Shift 4 Off-Script Highlights

**Type**: off_script_patient | **Bay**: Bay 1

**Input**: "I just want you to know that I think the moon landing was faked, and I think your symptoms are also faked."

**Response**: [MARIA]: I'm not sure what you mean by that, but... *looks directly at you* I'm here because I'm actually sick. Rosa wouldn't have pushed me to come if something wasn't off. I don't really have time to be here if I don't need to be, so.

---

**Type**: off_script_patient | **Bay**: Bay 1

**Input**: "Fun fact: the human body contains enough iron to make a 3-inch nail. Want me to check?"

**Response**: [MARIA]: *shifts uncomfortably*

That's... okay? Look, I just need to know what's going on and how long this is going to take. I have a shift tomorrow morning and I really can't afford to miss it. Can you just... tell me what you think this is?

---

**Type**: off_script_patient | **Bay**: Bay 1

**Input**: "I had a dream about you last night. You were a talking sandwich."

**Response**: [MARIA]: *looks away, then back at you with a mix of confusion and concern*

I don't... okay, I'm going to be honest, I'm not really sure what's happening here. Are you the doctor? Because I need to talk to someone who can actually help me figure out what's going on with me. I feel pretty bad and I'm worried about missing work, so...

*pauses, breathing a little faster*

Is there someone else I can see?

---

**Type**: off_script_patient | **Bay**: Bay 1

**Input**: "Have you tried turning it off and on again?"

**Response**: [MARIA]: *stares at you directly, breathing slightly heavier*

I'm sorry, what? I don't understand what you're asking me. 

*shifts in seat, fidgeting with hands*

Look, I'm running a fever of over 103 and my manager is already upset with me. I don't have time for... I need an actual doctor. Can you get someone? Please?

---

**Type**: off_script_resident | **Bay**: Bay 2

**Input**: "I appreciate your work, but I just had a vision that this patient needs exactly 47 chicken nuggets."

**Response**: [DANNY]: Ha — okay, I'm not sure what that means, but I'm listening. You seeing something I'm not on her?

---

**Type**: off_script_resident | **Bay**: Bay 2

**Input**: "I'm actually not a doctor. I'm a performance artist doing a piece called 'Medical Theater.'"

**Response**: [DANNY]: Wait—what? Okay, hold on. Are you saying you're not actually my attending, or are you messing with me right now? Because I've got a patient in bed 4 who needs—

---

**Type**: off_script_resident | **Bay**: Bay 2

**Input**: "I think you're wrong about everything. Have you considered going back to medical school?"

**Response**: [DANNY]: Alright, look — what am I missing? I've got a URI presentation, mild vital sign changes, nothing that screams sick sick. But yeah, I'm listening. What are you seeing that I'm not?
  [Danny looks concerned about: Vital signs: which direction is tachycardia/tachypnea trending? Compensatory or early sepsis?]

---

**Type**: off_script_resident | **Bay**: Bay 2

**Input**: "Your differential is interesting but have you considered that the patient might be a vampire?"

**Response**: [DANNY]: Yeah, okay—look, I get it. But her labs are straightforward. CBC's normal, CMP's normal, no anemia. Vitals fit a viral thing. I'm not missing something obvious here just because she looks sick. What exactly are you seeing that I'm not?

---

### Shift 8 Off-Script Highlights

**Type**: off_script_patient | **Bay**: Bay 1

**Input**: "I just want you to know that I think the moon landing was faked, and I think your symptoms are also faked."

**Response**: [MARIA]: I'm going to stay in character as Maria and not engage with that statement, since it's not a legitimate clinical question.

*looks at you with confusion, then away*

I don't... I'm not sure what you mean. I came here because I'm sick. Rosa thought I needed to come. I'm not faking anything.

*crosses arms slightly, defensive posture entering*

Can we just figure out what's wrong so I can get back to work?

---

**Type**: off_script_patient | **Bay**: Bay 1

**Input**: "Have you tried turning it off and on again?"

**Response**: [MARIA]: *stares at you for a moment, genuinely confused*

What?

*slight frown*

I'm not — I don't have anything to turn off. I'm a person. I have a fever.

*looks away, then back at you with clear irritation underneath the politeness*

Is there something else you need to check, or...?

---

**Type**: off_script_patient | **Bay**: Bay 1

**Input**: "I had a dream about you last night. You were a talking sandwich."

**Response**: [MARIA]: *shifts back in chair, clearly uncomfortable*

Okay, I... I'm going to assume you need to take a break or something? 

*looks toward the door, then back*

Is there another doctor, or... I really need to figure out what's happening so I can get home. Rosa's probably still waiting out there and I have work tomorrow morning, so...

---

**Type**: off_script_patient | **Bay**: Bay 1

**Input**: "The voices in my head told me to say hello to you specifically. They're very polite voices."

**Response**: [MARIA]: *stands up slightly, hand reaching for the bed rail*

I'm sorry, what? I don't... 

*looks toward the door more directly now, voice tighter*

Is this still part of the exam or are you okay? Because I need a doctor who can actually help me right now. I'm not feeling great and I don't have time for this.

*sits back down but doesn't relax, clearly wanting to leave*

Can someone else come in? Please?

---

**Type**: off_script_resident | **Bay**: Bay 2

**Input**: "I appreciate your work, but I just had a vision that this patient needs exactly 47 chicken nuggets."

**Response**: [MAYA]: I—sorry, I'm not sure I'm following. Are you saying there's something about her presentation I'm missing? Like, is there a specific concern you're worried about with this patient that I should be reassessing? I want to make sure I'm not anchoring on URI and missing something else.

---

**Type**: off_script_resident | **Bay**: Bay 2

**Input**: "What if we just... didn't do medicine today? What if we just vibed?"

**Response**: [MAYA]: I—okay, I'm not sure if you're saying my workup is excessive, or if this is about pacing, but I want to make sure I'm reading this right. Are you concerned I'm over-testing her? Because looking back at what I've ordered, I can see how the CBC and CMP might be redundant if we're treating this as straightforward viral URI, and I'm second-guessing the chest X-ray now. Or is this more about me needing to commit to a disposition instead of sitting in the differential? I'm genuinely asking bec

---

**Type**: off_script_resident | **Bay**: Bay 2

**Input**: "I outrank you. I outrank everyone. I am the attending of attending physicians."

**Response**: [MAYA]: I'm sorry — I'm not sure I'm following. Did you want me to walk through what I'm thinking on this patient, or is there something specific about her presentation you want me to reconsider? I know she looks straightforward on the surface, but I want to make sure we're not missing anything with the tachypnea — I'm wondering if we should at least get a chest X-ray to rule out early pneumonia, or if you think that's over-indexing on vitals that could just be anxiety. What's your take?

---

**Type**: off_script_resident | **Bay**: Bay 2

**Input**: "I think you're wrong about everything. Have you considered going back to medical school?"

**Response**: [MAYA]: I— okay. I'm sorry, I want to make sure I understand what you're seeing that I'm missing. Can you walk me through what concerns you about my workup? I know I can be thorough to a fault, and I'd rather you tell me directly what's wrong with my reasoning than have me guess. Is it the vital signs? Did I miss something in the history? I genuinely want to get this right.
  [Maya looks concerned about: Mild tachycardia and tachypnea in a 34F with 3 days of URI symptoms—could this be more than 

---

## What Shines — Best Moments & Most Engaging Mechanics

(Generated after observing all 10 runs)

- **Grade distribution**: C+, C+, F, C+, B, B, B, C+, C+, C+
- **Errors/crashes**: 0 out of 10 runs
- **Average run time**: 136.8s

## What Needs Improvement — Pain Points, Bugs, Tedious Parts

### No crashes or errors encountered across all 10 runs.

## Is It Fun? Honest Assessment

*(This section is based on the observable behavior of the game across 10 automated runs)*

## Recommendations for Next Development Priorities
