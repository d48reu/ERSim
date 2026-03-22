"""
Hand-authored case seed templates for semi-procedural case generation.

Each template provides the medical 'spine' of a case — the diagnosis,
presentation pattern, acuity, and disposition that must remain consistent.
The LLM randomizes demographics, social context, narrative, and human detail
around this fixed medical truth.

Template fields:
    chief_complaint     What triage writes down
    age_range           (min, max) tuple for random age selection
    sex                 "M", "F", or "any"
    acuity_range        (min, max) tuple — 1 is sickest, 5 is mildest
    disposition         Where they end up if managed correctly
    true_diagnosis      Specific medical diagnosis (never vague)
    narrative_hook_template   A human-story seed the LLM expands
    classic_miss_reason Why a competent resident might miss this
    specialty_tags      List of relevant specialties
    variation_axes      What the LLM is free to randomize
    case_type           "standard", "red_herring" (scary but benign),
                        or "trap" (routine-looking but dangerous)
"""

CASE_TEMPLATES = [
    # ===================================================================
    # 1. CARDIOLOGY — NSTEMI masquerading as GI complaint (TRAP)
    # ===================================================================
    {
        "chief_complaint": "Epigastric discomfort and nausea",
        "age_range": (55, 78),
        "sex": "any",
        "acuity_range": (2, 3),
        "disposition": "cath-lab",
        "true_diagnosis": "NSTEMI with inferior wall involvement",
        "narrative_hook_template": "A person who's been ignoring something for weeks because someone else's crisis seemed more important than their own body.",
        "classic_miss_reason": "Anchoring on GI complaint — epigastric pain attributed to GERD or gastritis, especially if patient has GI history. ECG not ordered early because presentation seems non-cardiac.",
        "specialty_tags": ["cardiology", "GI"],
        "variation_axes": ["patient demographics", "occupation", "key_person", "social context", "what crisis they were prioritizing", "GI red herring history"],
        "case_type": "trap",
    },

    # ===================================================================
    # 2. CARDIOLOGY — SVT in young person (RED HERRING)
    # ===================================================================
    {
        "chief_complaint": "Heart racing, feels like it's going to explode",
        "age_range": (19, 32),
        "sex": "any",
        "acuity_range": (2, 3),
        "disposition": "discharge",
        "true_diagnosis": "Paroxysmal supraventricular tachycardia (AVNRT), hemodynamically stable",
        "narrative_hook_template": "Someone whose body just did something terrifying in the middle of an otherwise normal day, and they're now convinced something is fundamentally broken.",
        "classic_miss_reason": "Overreaction to the dramatic HR — ordering excessive workup or admitting for a rhythm that will convert with vagal maneuvers or adenosine. The scare is real but the danger is minimal.",
        "specialty_tags": ["cardiology"],
        "variation_axes": ["patient demographics", "what they were doing when it started", "occupation", "social context", "caffeine/stimulant use history"],
        "case_type": "red_herring",
    },

    # ===================================================================
    # 3. CARDIOLOGY — Aortic dissection
    # ===================================================================
    {
        "chief_complaint": "Sudden severe chest pain radiating to back",
        "age_range": (45, 72),
        "sex": "M",
        "acuity_range": (1, 1),
        "disposition": "OR",
        "true_diagnosis": "Stanford Type A aortic dissection",
        "narrative_hook_template": "A person who was in the middle of an argument when something tore inside them, and now neither the argument nor anything else matters.",
        "classic_miss_reason": "Initial ECG may show ST changes leading to ACS workup pathway. BP differential between arms not checked. CTA delayed while troponin is pending.",
        "specialty_tags": ["cardiology", "CT surgery"],
        "variation_axes": ["patient demographics", "what the argument was about", "occupation", "hypertension history", "key_person", "Marfan habitus"],
        "case_type": "standard",
    },

    # ===================================================================
    # 4. PULMONOLOGY — PE in young woman (TRAP)
    # ===================================================================
    {
        "chief_complaint": "Shortness of breath and chest tightness",
        "age_range": (22, 35),
        "sex": "F",
        "acuity_range": (2, 3),
        "disposition": "admit-floor",
        "true_diagnosis": "Bilateral subsegmental pulmonary embolism secondary to oral contraceptive use",
        "narrative_hook_template": "A woman who assumed the breathlessness was just stress because everything in her life has been stressful lately, and she's used to pushing through.",
        "classic_miss_reason": "Young healthy woman with anxiety — presentation attributed to panic attack. Tachycardia and dyspnea normalized as 'anxiety.' OCP use not elicited. D-dimer not ordered because pretest probability seems low.",
        "specialty_tags": ["pulmonology", "hematology"],
        "variation_axes": ["patient demographics", "occupation", "recent travel or immobility", "social stressors", "key_person", "reason she started OCPs"],
        "case_type": "trap",
    },

    # ===================================================================
    # 5. PULMONOLOGY — Spontaneous pneumothorax
    # ===================================================================
    {
        "chief_complaint": "Sudden sharp chest pain and difficulty breathing",
        "age_range": (18, 28),
        "sex": "M",
        "acuity_range": (2, 2),
        "disposition": "admit-floor",
        "true_diagnosis": "Primary spontaneous pneumothorax, moderate (30% collapse)",
        "narrative_hook_template": "A tall, thin person who felt something pop while doing nothing special, and now breathing feels like work for the first time in their life.",
        "classic_miss_reason": "In a young person with pleuritic chest pain, initial thought may be musculoskeletal. Decreased breath sounds on one side missed if exam is cursory. CXR delayed for lower-acuity triage.",
        "specialty_tags": ["pulmonology", "thoracic surgery"],
        "variation_axes": ["patient demographics", "what they were doing", "occupation", "smoking history", "living situation", "Marfanoid habitus"],
        "case_type": "standard",
    },

    # ===================================================================
    # 6. INFECTIOUS DISEASE — Necrotizing fasciitis (TRAP)
    # ===================================================================
    {
        "chief_complaint": "Leg pain and redness, getting worse",
        "age_range": (35, 65),
        "sex": "any",
        "acuity_range": (2, 3),
        "disposition": "OR",
        "true_diagnosis": "Necrotizing fasciitis (Type II, Group A Strep) of lower extremity",
        "narrative_hook_template": "A person who thought it was just a bug bite that got infected, and waited three days because they couldn't afford to miss work for something so small.",
        "classic_miss_reason": "Early nec fasc looks like cellulitis. Pain out of proportion to exam findings is the key clue — dismissed as patient being dramatic. Skin changes lag behind fascial plane involvement.",
        "specialty_tags": ["infectious disease", "surgery"],
        "variation_axes": ["patient demographics", "occupation", "initial wound/entry point", "diabetes or immunocompromise", "social context for delayed presentation", "key_person"],
        "case_type": "trap",
    },

    # ===================================================================
    # 7. INFECTIOUS DISEASE — Bacterial meningitis
    # ===================================================================
    {
        "chief_complaint": "Worst headache of my life, neck is stiff",
        "age_range": (18, 25),
        "sex": "any",
        "acuity_range": (1, 2),
        "disposition": "admit-icu",
        "true_diagnosis": "Acute bacterial meningitis (Neisseria meningitidis)",
        "narrative_hook_template": "A college student who thought the headache was from last night until the light started hurting and they couldn't touch their chin to their chest.",
        "classic_miss_reason": "Early presentation overlaps with migraine or viral illness. If patient is hungover or has recent URI, symptoms are normalized. LP delayed waiting for CT. Empiric antibiotics delayed for diagnostics.",
        "specialty_tags": ["infectious disease", "neurology"],
        "variation_axes": ["patient demographics", "college/dorm context", "recent social events", "key_person who brought them in", "vaccination status", "prodromal symptoms"],
        "case_type": "standard",
    },

    # ===================================================================
    # 8. INFECTIOUS DISEASE — Sepsis from UTI in elderly (TRAP)
    # ===================================================================
    {
        "chief_complaint": "Confusion and weakness",
        "age_range": (72, 90),
        "sex": "F",
        "acuity_range": (2, 3),
        "disposition": "admit-icu",
        "true_diagnosis": "Urosepsis with early septic shock secondary to complicated urinary tract infection (E. coli)",
        "narrative_hook_template": "A woman whose daughter visits every Sunday and found her mother not making sense for the first time, and neither wants to name what they're both afraid of.",
        "classic_miss_reason": "Altered mental status in elderly attributed to dementia, delirium from dehydration, or 'sundowning.' Vitals may show compensated sepsis (normal BP with tachycardia). UTI dismissed as incidental finding rather than source.",
        "specialty_tags": ["infectious disease", "urology", "geriatrics"],
        "variation_axes": ["patient demographics", "living situation", "key_person relationship", "baseline cognitive function", "recent antibiotic use", "catheter history"],
        "case_type": "trap",
    },

    # ===================================================================
    # 9. TOXICOLOGY — Acetaminophen overdose
    # ===================================================================
    {
        "chief_complaint": "Nausea and abdominal pain",
        "age_range": (16, 30),
        "sex": "any",
        "acuity_range": (2, 3),
        "disposition": "admit-icu",
        "true_diagnosis": "Acute acetaminophen hepatotoxicity (ingestion >150mg/kg, Rumack-Matthew nomogram above treatment line)",
        "narrative_hook_template": "A person who took something they shouldn't have and now regrets it, but can't figure out how to say that in a room where someone is watching.",
        "classic_miss_reason": "Patient presents in the early (0-24hr) phase when they look fine — nausea and vague abdominal pain. If ingestion is not disclosed, workup goes down GI path. APAP level not checked because patient doesn't volunteer the ingestion.",
        "specialty_tags": ["toxicology", "psych", "hepatology"],
        "variation_axes": ["patient demographics", "reason for ingestion (intentional vs accidental vs self-harm)", "who is in the waiting room", "what they're protecting", "occupation", "social context"],
        "case_type": "trap",
    },

    # ===================================================================
    # 10. TOXICOLOGY — Serotonin syndrome
    # ===================================================================
    {
        "chief_complaint": "Agitation, sweating, tremor",
        "age_range": (25, 55),
        "sex": "any",
        "acuity_range": (2, 2),
        "disposition": "admit-icu",
        "true_diagnosis": "Serotonin syndrome secondary to drug interaction (SSRI + tramadol/linezolid/triptans)",
        "narrative_hook_template": "A person who just started a new medication their doctor prescribed and thought the shaking and sweating was a bad reaction, not realizing their two prescriptions were fighting each other.",
        "classic_miss_reason": "Presentation mimics NMS, anticholinergic toxicity, or sympathomimetic overdose. Clonus and hyperreflexia are the distinguishing features but require a focused neuro exam. Medication reconciliation not completed early.",
        "specialty_tags": ["toxicology", "neurology"],
        "variation_axes": ["patient demographics", "which medications caused it", "prescriber context", "occupation", "key_person", "how they describe the symptoms"],
        "case_type": "standard",
    },

    # ===================================================================
    # 11. TRAUMA — Delayed splenic rupture in elderly on anticoagulants
    # ===================================================================
    {
        "chief_complaint": "Left shoulder pain after a fall yesterday",
        "age_range": (68, 85),
        "sex": "any",
        "acuity_range": (2, 3),
        "disposition": "OR",
        "true_diagnosis": "Delayed splenic rupture with hemoperitoneum (Grade III splenic laceration), anticoagulant-related coagulopathy",
        "narrative_hook_template": "An older person who fell yesterday and didn't think much of it, but the pain moved somewhere it shouldn't be, and they look grayer than they did an hour ago.",
        "classic_miss_reason": "Left shoulder pain after fall → orthopedic workup. Kehr's sign (referred diaphragmatic pain to shoulder) missed. Anticoagulant use makes minor mechanism dangerous. Delayed presentation means initial imaging may show only small amount of free fluid.",
        "specialty_tags": ["trauma", "surgery", "geriatrics"],
        "variation_axes": ["patient demographics", "mechanism of fall", "anticoagulant type", "living situation", "key_person", "why they delayed coming in"],
        "case_type": "trap",
    },

    # ===================================================================
    # 12. TRAUMA — Epidural hematoma with lucid interval
    # ===================================================================
    {
        "chief_complaint": "Hit my head, felt fine but now getting a headache",
        "age_range": (18, 45),
        "sex": "any",
        "acuity_range": (1, 2),
        "disposition": "OR",
        "true_diagnosis": "Acute epidural hematoma (middle meningeal artery) with lucid interval",
        "narrative_hook_template": "A person who got up after being hit and walked around fine for two hours, and now something is changing that they can feel but can't describe.",
        "classic_miss_reason": "The lucid interval is the trap — patient arrives alert and oriented, GCS 15. Mechanism may seem minor (sports injury, fall). Headache attributed to concussion. Progressive deterioration happens fast once it starts. CT delayed because patient 'looks fine.'",
        "specialty_tags": ["trauma", "neurosurgery"],
        "variation_axes": ["patient demographics", "mechanism of injury", "sport or activity", "who was with them", "occupation", "time elapsed since injury"],
        "case_type": "standard",
    },

    # ===================================================================
    # 13. PEDIATRICS — Intussusception in toddler
    # ===================================================================
    {
        "chief_complaint": "Intermittent crying and not eating",
        "age_range": (6, 36),  # months — generator prompt should specify age in months
        "sex": "any",
        "acuity_range": (2, 3),
        "disposition": "OR",
        "true_diagnosis": "Ileocolic intussusception",
        "narrative_hook_template": "A parent who knows something is wrong with their child but can't point to anything specific, because between the crying episodes the baby seems almost normal.",
        "classic_miss_reason": "Intermittent nature — child may appear well between episodes. Classic triad (pain, vomiting, currant jelly stool) present in <50% of cases. Attributed to colic or viral gastroenteritis. Abdominal exam may be benign between episodes.",
        "specialty_tags": ["pediatrics", "pediatric surgery"],
        "variation_axes": ["child demographics", "parent demographics", "how many episodes", "key_person bringing them in", "recent viral illness", "feeding history"],
        "case_type": "standard",
        "_age_unit": "months",
    },

    # ===================================================================
    # 14. PEDIATRICS — Viral croup (RED HERRING)
    # ===================================================================
    {
        "chief_complaint": "Barking cough and noisy breathing",
        "age_range": (1, 5),
        "sex": "any",
        "acuity_range": (3, 3),
        "disposition": "discharge",
        "true_diagnosis": "Viral croup (laryngotracheobronchitis), mild-moderate, Westley score 3",
        "narrative_hook_template": "A first-time parent whose child made a sound they've never heard before at 2 AM, and the drive to the ER felt like the longest drive of their life.",
        "classic_miss_reason": "The stridor sounds terrifying to parents and to new residents. Risk is over-investigating or admitting a child who needs dexamethasone and observation. The real miss would be epiglottitis, but the barking cough and gradual onset point to croup.",
        "specialty_tags": ["pediatrics", "ENT"],
        "variation_axes": ["child demographics", "parent demographics", "time of night", "first child vs experienced parent", "daycare exposure", "living situation"],
        "case_type": "red_herring",
    },

    # ===================================================================
    # 15. PEDIATRICS — Non-accidental trauma
    # ===================================================================
    {
        "chief_complaint": "Toddler fell off couch, arm swollen",
        "age_range": (8, 30),  # months
        "sex": "any",
        "acuity_range": (3, 3),
        "disposition": "admit-floor",
        "true_diagnosis": "Non-accidental trauma — spiral fracture of humerus with healing rib fractures on skeletal survey, inconsistent with stated mechanism",
        "narrative_hook_template": "A parent with a story that doesn't quite match the injury, and a child who is too quiet for their age.",
        "classic_miss_reason": "Accepting the stated mechanism without scrutiny. Not performing a skeletal survey. Spiral fracture in a pre-ambulatory child should raise red flags. Discomfort with the social implications of the diagnosis leads to avoidance.",
        "specialty_tags": ["pediatrics", "orthopedic", "social work"],
        "variation_axes": ["child demographics", "caregiver demographics", "stated mechanism", "which parent/caregiver brought them", "inconsistencies in story", "social context"],
        "case_type": "standard",
        "_age_unit": "months",
    },

    # ===================================================================
    # 16. OB/GYN — Ectopic pregnancy (TRAP)
    # ===================================================================
    {
        "chief_complaint": "Lower abdominal pain and light-headedness",
        "age_range": (20, 38),
        "sex": "F",
        "acuity_range": (2, 2),
        "disposition": "OR",
        "true_diagnosis": "Ruptured ectopic pregnancy (right tubal) with hemoperitoneum",
        "narrative_hook_template": "A woman who didn't know she was pregnant, or did know and hasn't told anyone, and now something has gone wrong that she can't explain away.",
        "classic_miss_reason": "Patient denies possibility of pregnancy or has recent negative home test. Abdominal pain attributed to ovarian cyst, appendicitis, or GI cause. Urine hCG not sent because pregnancy 'not possible.' Peritoneal signs develop insidiously.",
        "specialty_tags": ["OB/GYN", "surgery"],
        "variation_axes": ["patient demographics", "relationship status", "who knows about the pregnancy", "contraception history", "occupation", "key_person"],
        "case_type": "trap",
    },

    # ===================================================================
    # 17. OB/GYN — Placental abruption
    # ===================================================================
    {
        "chief_complaint": "Third trimester, abdominal pain and vaginal bleeding",
        "age_range": (22, 38),
        "sex": "F",
        "acuity_range": (1, 1),
        "disposition": "OR",
        "true_diagnosis": "Placental abruption (Grade 2 — moderate, with concealed hemorrhage component)",
        "narrative_hook_template": "A pregnant woman who felt something change inside her and knows it's not supposed to feel like this, and every minute in the waiting room feels like a betrayal.",
        "classic_miss_reason": "Visible bleeding may be modest if hemorrhage is concealed behind placenta. Fundal height increasing over time is the clue. Pain attributed to Braxton-Hicks or round ligament. Fetal monitoring shows late decelerations before maternal vitals decompensate.",
        "specialty_tags": ["OB/GYN"],
        "variation_axes": ["patient demographics", "gestational age", "prenatal care history", "hypertension/preeclampsia history", "key_person", "social context"],
        "case_type": "standard",
    },

    # ===================================================================
    # 18. PSYCH — Thyrotoxicosis presenting as panic attack (TRAP)
    # ===================================================================
    {
        "chief_complaint": "Panic attack, racing heart, can't calm down",
        "age_range": (25, 45),
        "sex": "F",
        "acuity_range": (3, 3),
        "disposition": "admit-floor",
        "true_diagnosis": "Thyroid storm (Burch-Wartofsky score >45) secondary to undiagnosed Graves' disease",
        "narrative_hook_template": "A woman who's been told she's anxious for years, and believed it, until today when her body did something anxiety doesn't explain.",
        "classic_miss_reason": "History of anxiety → presentation framed as psychiatric. Tachycardia and agitation normalized as panic. Fever attributed to the agitation. TSH not checked because 'this is clearly psych.' Weight loss and tremor attributed to stress.",
        "specialty_tags": ["psych", "endocrinology"],
        "variation_axes": ["patient demographics", "psychiatric history", "recent life stressors", "occupation", "key_person", "prior ED visits for 'anxiety'"],
        "case_type": "trap",
    },

    # ===================================================================
    # 19. PSYCH — Acute psychotic episode
    # ===================================================================
    {
        "chief_complaint": "Acting bizarre, talking to people who aren't there",
        "age_range": (18, 28),
        "sex": "M",
        "acuity_range": (2, 3),
        "disposition": "admit-floor",
        "true_diagnosis": "First-break psychosis (schizophreniform disorder), ruling out substance-induced psychotic disorder and anti-NMDA receptor encephalitis",
        "narrative_hook_template": "A young person whose family has been watching them change for months and today was the day it became undeniable.",
        "classic_miss_reason": "Attributing symptoms to drug use without checking for organic causes. Anti-NMDA receptor encephalitis mimics primary psychosis in young adults. Incomplete workup — needs MRI, LP, and NMDA antibodies. Cannabis use history used to explain everything.",
        "specialty_tags": ["psych", "neurology"],
        "variation_axes": ["patient demographics", "prodromal changes family noticed", "substance use history", "college/employment context", "key_person", "family psychiatric history"],
        "case_type": "standard",
    },

    # ===================================================================
    # 20. GI — Ascending cholangitis
    # ===================================================================
    {
        "chief_complaint": "Fever, right upper quadrant pain, yellowish skin",
        "age_range": (45, 75),
        "sex": "any",
        "acuity_range": (2, 2),
        "disposition": "admit-icu",
        "true_diagnosis": "Ascending cholangitis secondary to choledocholithiasis (Charcot's triad progressing to Reynolds' pentad)",
        "narrative_hook_template": "A person who thought the stomach pain would pass like it always does, until the fever started and their eyes turned yellow and they realized this time was different.",
        "classic_miss_reason": "Charcot's triad (fever, jaundice, RUQ pain) is classic but the full triad may not be present early. If only pain and fever, workup may pursue other sources. Delayed ERCP while pursuing conservative management of 'cholecystitis.'",
        "specialty_tags": ["GI", "surgery"],
        "variation_axes": ["patient demographics", "prior gallstone history", "occupation", "key_person", "how long they waited", "social context"],
        "case_type": "standard",
    },

    # ===================================================================
    # 21. GI — Boerhaave syndrome (esophageal perforation)
    # ===================================================================
    {
        "chief_complaint": "Severe chest pain after vomiting",
        "age_range": (35, 65),
        "sex": "M",
        "acuity_range": (1, 2),
        "disposition": "OR",
        "true_diagnosis": "Boerhaave syndrome (spontaneous esophageal perforation with left-sided pneumomediastinum)",
        "narrative_hook_template": "A person who was vomiting from drinking too much and then something changed — the pain became something else entirely, and now they're sicker than any hangover should make them.",
        "classic_miss_reason": "Chest pain after vomiting in a drinker → ACS or Mallory-Weiss tear assumed. Subcutaneous emphysema in the neck (Hamman's sign) missed on exam. CXR may show pleural effusion but mediastinal air is subtle. CT with oral contrast needed but not ordered.",
        "specialty_tags": ["GI", "thoracic surgery"],
        "variation_axes": ["patient demographics", "alcohol use context", "occupation", "social context for the drinking", "key_person", "time from onset to presentation"],
        "case_type": "standard",
    },

    # ===================================================================
    # 22. NEURO — Posterior circulation stroke as vertigo (TRAP)
    # ===================================================================
    {
        "chief_complaint": "Room is spinning, nausea, unsteady on feet",
        "age_range": (50, 75),
        "sex": "any",
        "acuity_range": (2, 3),
        "disposition": "admit-icu",
        "true_diagnosis": "Posterior inferior cerebellar artery (PICA) stroke presenting as acute vestibular syndrome",
        "narrative_hook_template": "A person who woke up and the room wouldn't stop moving, and they assumed it was the inner ear thing their friend had, but this doesn't feel like what their friend described.",
        "classic_miss_reason": "Vertigo + nausea + nystagmus = 'peripheral vertigo' or 'labyrinthitis.' HINTS exam (Head Impulse, Nystagmus, Test of Skew) not performed — this is the key differentiator. Central nystagmus pattern missed. CT is insensitive for posterior fossa strokes; MRI needed.",
        "specialty_tags": ["neurology", "ENT"],
        "variation_axes": ["patient demographics", "vascular risk factors", "occupation", "what they were doing when it started", "key_person", "prior vertigo history"],
        "case_type": "trap",
    },

    # ===================================================================
    # 23. NEURO — Subarachnoid hemorrhage
    # ===================================================================
    {
        "chief_complaint": "Thunderclap headache, worst of my life",
        "age_range": (35, 60),
        "sex": "any",
        "acuity_range": (1, 2),
        "disposition": "admit-icu",
        "true_diagnosis": "Aneurysmal subarachnoid hemorrhage (anterior communicating artery aneurysm rupture)",
        "narrative_hook_template": "A person who was doing something ordinary when the headache hit like a switch being thrown, and they knew immediately this wasn't a headache.",
        "classic_miss_reason": "If headache is improving on arrival, attributed to migraine or tension headache. CT sensitivity drops after 6 hours. LP not performed after negative CT. Small 'sentinel bleed' pattern may show subtle findings.",
        "specialty_tags": ["neurology", "neurosurgery"],
        "variation_axes": ["patient demographics", "what they were doing at onset", "family history of aneurysm", "occupation", "key_person", "headache history"],
        "case_type": "standard",
    },

    # ===================================================================
    # 24. ORTHOPEDIC — Compartment syndrome
    # ===================================================================
    {
        "chief_complaint": "Leg pain after injury, getting worse despite pain meds",
        "age_range": (18, 45),
        "sex": "any",
        "acuity_range": (2, 2),
        "disposition": "OR",
        "true_diagnosis": "Acute anterior compartment syndrome of the lower leg following tibial shaft fracture",
        "narrative_hook_template": "A person with a broken leg whose pain is doing something the fracture doesn't explain, and the nurses are giving the maximum morphine dose and it's not touching it.",
        "classic_miss_reason": "Pain attributed to the fracture itself. The 5 Ps (pain, pressure, paralysis, paresthesia, pulselessness) are late findings — waiting for all of them means waiting too long. Pain out of proportion to injury and pain with passive stretch are early signs. Pulselessness is a pre-amputation finding, not a diagnostic criterion.",
        "specialty_tags": ["orthopedic", "surgery"],
        "variation_axes": ["patient demographics", "mechanism of injury", "sport or activity", "time since injury", "key_person", "occupation"],
        "case_type": "standard",
    },

    # ===================================================================
    # 25. ORTHOPEDIC — Cauda equina syndrome (TRAP)
    # ===================================================================
    {
        "chief_complaint": "Bad back pain, hard to walk",
        "age_range": (35, 60),
        "sex": "any",
        "acuity_range": (2, 3),
        "disposition": "OR",
        "true_diagnosis": "Cauda equina syndrome secondary to large central L4-L5 disc herniation with urinary retention",
        "narrative_hook_template": "A person who's had back pain for years and this time something is different — something below the waist isn't working right, but they're embarrassed to say what.",
        "classic_miss_reason": "Chronic back pain patient in the ED → 'drug seeking' or 'frequent flyer' bias. Saddle anesthesia and urinary symptoms not elicited because they aren't volunteered and provider doesn't ask. Post-void residual not checked. Rectal tone not assessed.",
        "specialty_tags": ["orthopedic", "neurosurgery"],
        "variation_axes": ["patient demographics", "chronic pain history", "occupation", "what's different this time", "bladder/bowel symptoms they're hiding", "key_person"],
        "case_type": "trap",
    },

    # ===================================================================
    # 26. DERM — Stevens-Johnson Syndrome
    # ===================================================================
    {
        "chief_complaint": "Rash spreading fast, mouth sores, eyes burning",
        "age_range": (20, 55),
        "sex": "any",
        "acuity_range": (2, 2),
        "disposition": "admit-icu",
        "true_diagnosis": "Stevens-Johnson Syndrome (SJS) secondary to newly started medication (allopurinol/lamotrigine/sulfonamide), BSA involvement 6%",
        "narrative_hook_template": "A person who started a new pill two weeks ago and now their skin is turning against them, and each hour brings something worse.",
        "classic_miss_reason": "Early SJS looks like a drug rash or viral exanthem. Mucosal involvement (oral, ocular, genital) is the key differentiator from simple drug eruption. Nikolsky sign not tested. Dermatology consult delayed because 'it's just a rash.'",
        "specialty_tags": ["derm", "burn/ICU"],
        "variation_axes": ["patient demographics", "which medication caused it", "reason for the medication", "occupation", "key_person", "timeline of rash spread"],
        "case_type": "standard",
    },

    # ===================================================================
    # 27. ENT — Peritonsillar abscess
    # ===================================================================
    {
        "chief_complaint": "Sore throat, can barely swallow, voice sounds weird",
        "age_range": (16, 35),
        "sex": "any",
        "acuity_range": (3, 3),
        "disposition": "discharge",
        "true_diagnosis": "Peritonsillar abscess (left), requiring needle aspiration and drainage",
        "narrative_hook_template": "A person who thought it was just a bad sore throat until they couldn't swallow their own spit and their voice changed and someone said 'you need to go to the ER.'",
        "classic_miss_reason": "Sore throat in a young person → rapid strep, antibiotics, discharge. Trismus, uvular deviation, and 'hot potato voice' not recognized. Failure to examine the posterior pharynx carefully. Risk of airway compromise underestimated.",
        "specialty_tags": ["ENT"],
        "variation_axes": ["patient demographics", "duration of sore throat before abscess", "prior antibiotic use", "who told them to come in", "occupation", "social context"],
        "case_type": "standard",
    },

    # ===================================================================
    # 28. UROLOGY — Testicular torsion
    # ===================================================================
    {
        "chief_complaint": "Sudden severe pain in my groin",
        "age_range": (12, 22),
        "sex": "M",
        "acuity_range": (2, 2),
        "disposition": "OR",
        "true_diagnosis": "Left testicular torsion (720 degrees), within salvage window (<6 hours)",
        "narrative_hook_template": "A teenage boy who is in too much pain to be embarrassed, but his parent is doing the talking and he can't bring himself to say where it actually hurts.",
        "classic_miss_reason": "Groin pain in a young male → hernia or musculoskeletal. Patient or parent may say 'groin' or 'stomach' without specifying testicular pain due to embarrassment. Cremasteric reflex not checked. Ultrasound ordered but takes time — this is a clinical diagnosis with a 6-hour window.",
        "specialty_tags": ["urology", "pediatrics"],
        "variation_axes": ["patient demographics", "who brought them in", "activity at onset", "how they describe the location", "social context", "time since onset"],
        "case_type": "standard",
    },

    # ===================================================================
    # 29. CARDIOLOGY — Benign chest pain (RED HERRING)
    # ===================================================================
    {
        "chief_complaint": "Chest pain, sharp, worse with breathing",
        "age_range": (22, 35),
        "sex": "any",
        "acuity_range": (4, 4),
        "disposition": "discharge",
        "true_diagnosis": "Acute pericarditis (viral, idiopathic) — benign, self-limited",
        "narrative_hook_template": "A person convinced they're having a heart attack at an age when it shouldn't happen, and the fear is more debilitating than the pain.",
        "classic_miss_reason": "Over-investigation — troponin may be mildly elevated (myopericarditis) leading to ACS pathway activation. The key is recognizing the pleuritic, positional nature and diffuse ST elevation with PR depression on ECG. Risk is unnecessary cath lab activation.",
        "specialty_tags": ["cardiology"],
        "variation_axes": ["patient demographics", "recent viral illness", "occupation", "family cardiac history driving their fear", "key_person", "social context"],
        "case_type": "red_herring",
    },

    # ===================================================================
    # 30. GI — Appendicitis
    # ===================================================================
    {
        "chief_complaint": "Stomach pain that moved to the right side",
        "age_range": (15, 40),
        "sex": "any",
        "acuity_range": (3, 3),
        "disposition": "OR",
        "true_diagnosis": "Acute uncomplicated appendicitis with focal peritonitis",
        "narrative_hook_template": "A person who's been trying to push through the pain for a day because they have something tomorrow they can't miss, and the pain just won the argument.",
        "classic_miss_reason": "Early appendicitis presents with periumbilical pain before localizing — if seen early, may be sent home as gastroenteritis. Atypical location in retrocecal appendix can mimic UTI or back pain. Women of childbearing age: ectopic must be ruled out first.",
        "specialty_tags": ["GI", "surgery"],
        "variation_axes": ["patient demographics", "what event they can't miss", "occupation", "duration of symptoms", "key_person", "eating/appetite history"],
        "case_type": "standard",
    },

    # ===================================================================
    # 31. NEURO — Benign positional vertigo (RED HERRING)
    # ===================================================================
    {
        "chief_complaint": "Dizzy when I roll over in bed, room spinning",
        "age_range": (40, 70),
        "sex": "any",
        "acuity_range": (4, 5),
        "disposition": "discharge",
        "true_diagnosis": "Benign paroxysmal positional vertigo (BPPV), posterior canal",
        "narrative_hook_template": "A person who thought they were having a stroke because the room lurched sideways when they sat up, and they lay perfectly still for an hour before calling someone.",
        "classic_miss_reason": "Over-investigation — CT/MRI ordered for what is a clinical diagnosis treatable with the Epley maneuver. The patient's fear drives unnecessary workup. Key is that vertigo is brief (<60 seconds), triggered by position change, and Dix-Hallpike is positive. No central signs.",
        "specialty_tags": ["neurology", "ENT"],
        "variation_axes": ["patient demographics", "what they were doing", "stroke fear context", "occupation", "key_person who called 911", "prior episodes"],
        "case_type": "red_herring",
    },

    # ===================================================================
    # 32. DERM/INFECTIOUS — Herpes zoster (shingles)
    # ===================================================================
    {
        "chief_complaint": "Burning pain on one side of my chest, now a rash",
        "age_range": (55, 80),
        "sex": "any",
        "acuity_range": (4, 4),
        "disposition": "discharge",
        "true_diagnosis": "Herpes zoster (shingles), T4-T6 dermatomal distribution, without ophthalmic involvement",
        "narrative_hook_template": "A person who thought the burning was their heart until the blisters appeared, and now they're relieved it's not cardiac but the pain is worse than they expected shingles to be.",
        "classic_miss_reason": "Before the rash appears, the prodromal pain can be mistaken for MI, pleurisy, or radiculopathy. Once vesicles appear, diagnosis is straightforward. The miss is in the pre-rash phase. In immunocompromised patients, disseminated zoster must be considered.",
        "specialty_tags": ["derm", "infectious disease"],
        "variation_axes": ["patient demographics", "immunocompromised status", "vaccination history", "occupation", "key_person", "days of pain before rash"],
        "case_type": "standard",
    },

    # ===================================================================
    # 33. PSYCH/SOCIAL — Domestic violence presenting as fall
    # ===================================================================
    {
        "chief_complaint": "Fell down stairs, facial bruising and rib pain",
        "age_range": (22, 50),
        "sex": "F",
        "acuity_range": (3, 3),
        "disposition": "discharge",
        "true_diagnosis": "Multiple contusions and non-displaced rib fractures (ribs 7-8 left), injuries inconsistent with stated mechanism — intimate partner violence",
        "narrative_hook_template": "A woman whose story about falling doesn't match her injuries, and the person who drove her here is sitting in the waiting room asking the front desk how much longer.",
        "classic_miss_reason": "Accepting the stated mechanism without questioning inconsistencies. Defensive injuries on forearms not documented. Partner in waiting room creating time pressure. Screening questions not asked when patient is alone. Provider discomfort with the social complexity.",
        "specialty_tags": ["trauma", "psych", "social work"],
        "variation_axes": ["patient demographics", "stated mechanism details", "partner characteristics", "children at home", "occupation", "prior ED visits", "injury pattern"],
        "case_type": "standard",
    },

    # ===================================================================
    # 34. PULM/ID — Community-acquired pneumonia with empyema
    # ===================================================================
    {
        "chief_complaint": "Cough, fever, chest pain for five days",
        "age_range": (40, 70),
        "sex": "any",
        "acuity_range": (2, 3),
        "disposition": "admit-floor",
        "true_diagnosis": "Community-acquired pneumonia (Streptococcus pneumoniae) complicated by parapneumonic effusion progressing to early empyema",
        "narrative_hook_template": "A person who treated their pneumonia with over-the-counter medicine and willpower for five days because they don't have insurance, and now they can't lie flat without drowning.",
        "classic_miss_reason": "CXR shows pneumonia — antibiotics started, feels like the job is done. Effusion on CXR attributed to 'reactive' rather than infected. Thoracentesis not performed. Patient clinically worsens on antibiotics alone because the empyema needs drainage.",
        "specialty_tags": ["pulmonology", "infectious disease"],
        "variation_axes": ["patient demographics", "insurance/access barriers", "occupation", "how long they waited", "key_person", "smoking history", "comorbidities"],
        "case_type": "standard",
    },

    # ===================================================================
    # 35. UROLOGY/GI — Kidney stone (RED HERRING-ish, routine)
    # ===================================================================
    {
        "chief_complaint": "Worst flank pain of my life, can't hold still",
        "age_range": (25, 55),
        "sex": "M",
        "acuity_range": (3, 4),
        "disposition": "discharge",
        "true_diagnosis": "Acute renal colic — 4mm distal ureteral calculus, non-obstructing, likely to pass spontaneously",
        "narrative_hook_template": "A person writhing in pain who looks like they're dying but has a problem that will fix itself with fluids and time, and the challenge is convincing them they're going to be okay.",
        "classic_miss_reason": "The dramatic presentation (10/10 pain, writhing, diaphoretic) can trigger extensive workup for AAA or other emergencies. The risk is the other direction too — assuming kidney stone and missing an AAA in an older patient with first-episode flank pain. In this case, it really is a stone.",
        "specialty_tags": ["urology"],
        "variation_axes": ["patient demographics", "prior stone history", "occupation", "hydration habits", "key_person", "pain tolerance and expression style"],
        "case_type": "red_herring",
    },
]


def get_template_by_index(index: int) -> dict:
    """Return a template by its index in the list."""
    return CASE_TEMPLATES[index % len(CASE_TEMPLATES)]


def get_templates_by_specialty(specialty: str) -> list[dict]:
    """Return all templates matching a given specialty tag."""
    specialty_lower = specialty.lower()
    return [
        t for t in CASE_TEMPLATES
        if any(specialty_lower in tag.lower() for tag in t["specialty_tags"])
    ]


def get_templates_by_type(case_type: str) -> list[dict]:
    """Return all templates of a given type (standard, red_herring, trap)."""
    return [t for t in CASE_TEMPLATES if t.get("case_type") == case_type]


def get_random_templates(n: int, avoid_indices: set[int] | None = None) -> list[tuple[int, dict]]:
    """
    Return n random (index, template) pairs, avoiding specified indices.
    Returns fewer than n if the pool is exhausted.
    """
    import random
    avoid = avoid_indices or set()
    available = [(i, t) for i, t in enumerate(CASE_TEMPLATES) if i not in avoid]
    random.shuffle(available)
    return available[:n]
