ACT-R is meant to be an integrated cognitive architecture: not just a model of one task, but a framework for constructing models that behave in human-like ways across tasks.

---

## 2. Cognitive architectures

### What is a cognitive architecture?

A cognitive architecture is basically the **infrastructure for an intelligent system**. It specifies cognitive functions that stay relatively constant across time and across different task domains.

Analogy from lecture: like the architecture of a building, car, or computer. Individual tasks/models change, but the underlying architecture stays.

### Unified theories of cognition

Goal = explain intelligent behavior at the **system level**, rather than having a disconnected theory for every individual phenomenon.

Newell's point: you cannot understand cognition by asking nature a sequence of isolated questions and hoping the answers automatically form a complete theory.

### Integrated / embodied cognition

Cognition does **not** operate in isolation. It interacts with:

- perception
- motor action
- audition
- the external environment

So perceptual and motor systems are not merely passive "input" and "output" devices. The environment and the body's interactions with it matter to the cognitive process.

### Why build a cognitive architecture?

Applications/motivations mentioned in the lecture:

1. **Philosophy** - unified understanding of mind.
2. **Psychology** - account for experimental data.
3. **Education** - cognitive models for intelligent tutoring / learning environments.
4. **HCI** - evaluate artifacts and help design them.
5. **Computer-generated forces** - cognitive agents in games/training environments.
6. **Neuroscience** - framework for interpreting brain-imaging data.

### Requirements

A useful cognitive architecture should aim for:

- integration of cognition + perception + action
- real-time operation
- robustness to errors, surprises, and unknown situations
- parameter-free (or increasingly constrained) behavioral predictions
- learning

### Time scale idea

Newell's amended time scale spans from days/hours down to milliseconds.

Important ACT-R-ish region:

- ~seconds: microstrategies / embodied activities
- ~1/3 sec: basic embodied activities
- ~100 ms: production-rule scale (the slide labels a production rule around this band)
- ~10 ms and below: architectural / subsymbolic elements and parameters

So ACT-R connects relatively high-level symbolic cognition to faster subsymbolic mechanisms.

---

## 3. Where ACT-R fits

Computational cognitive models can be connectionist, symbolic, mathematical, etc. Within symbolic approaches, cognitive architectures include production systems.

The tutorial positions ACT-R as a **hybrid production-system architecture** (symbolic + subsymbolic).

Other architectures mentioned:

- **Soar** - production rules, operators/problem spaces, goal-oriented/subgoaling, chunking as a learning mechanism.
- **EPIC** - parallel firing of production rules; strong visual and motor systems.

### ACT-R overview in four words

- **Modular**
- **Knowledge representation**
- **Symbolic + subsymbolic**
- **Performance + learning**

A cognitive model is presented as a computational process that **thinks/acts like a person**. Integrated models can also be connected to realistic tasks/devices (e.g. driving + phone interaction).

The driving example compares model predictions with human lane-deviation data. The point seems to be that an integrated cognitive model can predict effects of different interaction modes, not just execute an abstract task.

---

## 4. ACT-R architecture

### Evolution

The framework developed from HAM through ACT-E, ACT*, ACT-R, ACT-R 4/5, and ACT-R 6. The tutorial emphasizes that ACT-R has been used for a large number of models across perception, memory, problem solving, language, workload, fMRI, etc.

### ACT-R 6.0 modules and buffers

Core idea: **modules do specialized processing; buffers are the interfaces through which the production system accesses module information.**

The architecture diagram associates some components with brain regions:

- intentional module -> **goal buffer** (DLPFC)
- declarative module (temporal/hippocampus) -> **retrieval buffer** (VLPFC)
- productions / basal ganglia -> matching (striatum), selection (pallidum), execution (thalamus)
- visual module (occipital/etc.) -> **visual buffer** (parietal)
- manual module (motor/cerebellum) -> **manual buffer** (motor)
- all ultimately interact with the **environment**

### ACT-R assumption space

Two important distinctions cross each other:

1. **Declarative vs. procedural**
2. **Symbolic vs. subsymbolic**

For performance:

- symbolic declarative = retrieval of chunks
- symbolic procedural = application of production rules
- subsymbolic declarative = noisy activations controlling retrieval speed/accuracy
- subsymbolic procedural = noisy utilities controlling choice

For learning:

- symbolic declarative = encoding environment / caching goals
- symbolic procedural = production compilation
- subsymbolic declarative + procedural = Bayesian/statistical learning mechanisms

---

## 5. Knowledge representation: chunks vs. productions

### Declarative knowledge = chunks

Chunks are configurations of a small number of elements/slots.

Example addition fact:

```lisp
(CHUNK-TYPE addition-fact addend1 addend2 sum)
(CHUNK-TYPE integer value)

(ADD-DM
  (fact3+4
    isa addition-fact
    addend1 three
    addend2 four
    sum seven)
  (three
    isa integer
    value 3)
  (four
    isa integer
    value 4)
  (seven
    isa integer
    value 7))
```

Conceptually:

`fact3+4` is an `addition-fact` whose `addend1 -> three`, `addend2 -> four`, and `sum -> seven`.

**Note:** chunks represent facts/structured declarative information; slot values can point to other chunks.

### Procedural knowledge = production rules

A production is a **condition-action rule** with variables.

Addition example in plain English:

> IF the goal is to add the numbers in a column and `n1 + n2` are in the column, THEN retrieve the sum of `n1` and `n2`.

Productions coordinate information from declarative memory and the environment and transform the current goal state.

The lecture characterizes a production as:

- a small step of cognition
- a source of a serial bottleneck in an otherwise partly parallel system
- a condition-action data structure
- a specification of information flow involving cortex and basal ganglia

General structure:

```lisp
(p production-name
   ;; conditions / buffer tests
   ...
==>
   ;; actions / buffer transformations
   ...)
```

Key production properties listed: **modularity, abstraction, goal/buffer factoring, conditional asymmetry**.

---

## 6. Buffers and modules

### Buffers in ACT-R 6.0

1. **Goal buffer**
   - represents where the model is in the task
   - preserves information across production cycles

2. **Retrieval buffer**
   - holds information retrieved from declarative memory
   - activation calculations are central to retrieval

3. **Visual buffers**
   - visual-location = where something is
   - visual = the attended visual object
   - switching attention corresponds to buffer transformations

4. **Auditory / aural buffers**
   - broadly analogous to vision

5. **Manual buffer**
   - supports manual movement
   - includes movement preparation, Fitts' law, device properties

6. **Vocal buffer**
   - analogous to manual, but less developed in this tutorial

7+. Additional buffers can be added when needed (e.g. time).

---

## 7. Cognition and the production-system cycle

Executive control is the **production system**.

Important tension:

- cognition / production firing is **serial**
- subsymbolic processing can occur **in parallel**

When several productions could fire, **utility** determines which one is selected.

Basic cycle:

1. Match conditions of all productions against current buffers.
2. Matching productions enter the **conflict set**.
3. Conflict resolution chooses one production.
4. Its action side initiates changes to one or more buffers.
5. Repeat while a production can match or an action is still in progress.

### Goal-directed behavior

The goal represents what the system is currently trying to do. It is a declarative-memory element that becomes the focus of "internal" attention.

---

## 8. Declarative memory

Memory retrieval is **activation-based**.

Factors mentioned early in the tutorial:

- frequency
- recency
- contextual cues

Process:

1. Cognition requests a retrieval and specifies constraints.
2. Partial matching can be allowed.
3. Memory searches in parallel for chunks matching the constraints.
4. Activation is calculated.
5. The most active suitable chunk is returned.

**Key idea:** declarative memory is not just an exact database lookup. Retrieval likelihood and latency depend on experience, context, matching, and noise.

---

## 9. Vision

ACT-R's vision module = its "eyes."

Two systems:

- dorsal **where** system
- ventral **what** system

### "Where" system

Cognition requests a pre-attentive visual search using constraints, e.g.:

- color = red
- screen-x > 150
- other properties / spatial locations

The system returns a **location chunk** for an object satisfying those constraints.

### "What" system

Given a location chunk:

1. cognition requests a move of attention
2. visual attention shifts to that location
3. the object is encoded
4. encoding is placed in the visual buffer
5. an episodic representation can be added to declarative memory
6. latency is calculated (the slide mentions EMMA)

---

## 10. Motor system

ACT-R's motor module = its "hands" and is based on EPIC's manual motor processor.

Movement styles:

- **ply** - move a device such as a mouse to a location
- **punch** - press a key already below a finger
- **peck** - move a finger to a location and press
- **peck-recoil** - peck, then return finger
- **point-hand** - move the hand to a new location

### Phased processing

**Preparation phase**

- hierarchical feature preparation: style -> hand -> finger
- time depends on movement complexity / number of features
- state becomes preparation-busy

**Initiation**

- fixed 50 ms in the tutorial

**Execution**

- depends on movement type, minimum execution time, and distance
- distance effects can follow **Fitts' law**
- preparation and execution can overlap

### Device interface

ACT-R can interact with a simulated device/window containing graphical objects. The interface constructs visual iconic-memory features and handles mouse/keyboard actions.

---

## 11. Audition

The audition module simulates auditory perception.

It stores temporal sound features and can represent tones, digits, and speech. Attributes include onset, duration, delay, and recode time.

Processing parallels vision:

1. cognition specifies constraints
2. audition returns a location chunk
3. cognition shifts auditory attention to it
4. audition encodes the sound

---

## 12. Symbolic vs. subsymbolic ACT-R

The **symbolic level** says *what structures/rules exist* (chunks, productions, buffers).

The **subsymbolic level** helps determine *which thing wins, how fast, and with what variability*.

Two major quantities:

- **production utilities** -> which production is selected during conflict
- **chunk activations** -> which chunk is retrieved and how long retrieval takes

Parameters mentioned include:

- utility/activation noise
- activation learning from frequency + recency
- utility learning from probability + cost
- utility and activation thresholds

---

## 13. Chunk activation

General activation equation shown in the tutorial:

```text
Ai = Bi + sum_j(Wj * Sji) + sum_k(MPk * Simkl) + N(0,s)
```

Interpretation:

- `Bi` = **base-level activation**
- `Wj * Sji` = **source/associative activation** from context
- `MPk * Simkl` = **partial-matching / mismatch contribution**
- `N(0,s)` = **noise**

### What activation means

Activation makes chunks available according to how useful past experience suggests they will be **right now**.

Components:

- base-level -> general past access/usefulness
- associative activation -> relevance to current context
- matching penalty -> closeness to requested match
- noise -> stochastic variability

### Activation and retrieval

- retrieval time decreases exponentially as activation rises
- retrieval probability follows a Boltzmann/softmax-like distribution
- highest-activation chunk is retrieved only if it reaches the retrieval threshold `tau`

So: **higher activation -> generally faster and more likely retrieval.**

### Base-level activation

`Bi` estimates the context-independent likelihood/log-odds that chunk `Ci` will be needed.

Determined especially by:

- **frequency** of use
- **recency** of use

Base-level learning assumes the need for a fact decays as a power function of time since use; repeated uses contribute together. The tutorial notes `d = .5` is used in many ACT-R models.

### Source activation

`Wj` reflects attention given to elements in the current goal/context. ACT-R assumes a limited/fixed capacity for this source activation.

### Associative strengths

`Sji` represents how predictive/contextually useful chunk `Cj` is as a source of activation for retrieving `Ci`.

### Partial matching

Mismatch penalty controls how strict retrieval is:

- `MP = 0` -> free association
- very large `MP` -> near-perfect matching
- intermediate -> permit imperfect matches

Similarity values compare the requested value with the value in a candidate chunk, allowing generalization.

### Noise

Noise is not merely error; it models variability in human behavior and can help exploration.

Two types mentioned:

- permanent noise -> encoding variability
- transient noise -> moment-to-moment variability

---

## 14. Production utility / conflict resolution

ACT-R needs to choose between competing productions.

Tutorial equation:

```text
Expected Gain E = P*G - C
```

where:

- `P` = expected probability of success
- `G` = value of the goal
- `C` = expected cost

Choice among productions is probabilistic (Boltzmann-like), with noise/temperature affecting how deterministic the choice is.

The probability estimate is based on successes vs. failures, including prior and experienced successes/failures.

### Decay of experience

Older successes and failures are discounted over time. The lecture stresses that this **temporal weighting is critical in the real world**.

Student interpretation: utility learning lets ACT-R adapt strategy choice based on which actions have recently worked and how costly they have been.

---

## 15. Production compilation

Production compilation is ACT-R's procedural-learning mechanism for combining/transforming sequences of productions into more direct productions.

Basic intuition from the example:

- initially: see stimulus -> request memory retrieval -> wait for result -> respond
- after learning/compilation: a more specific production can sometimes map a familiar stimulus directly to the response

This can make practiced behavior more efficient.

Principles listed in the lecture:

1. **Perceptual-motor buffers:** avoid combinations that would jam by requiring two incompatible operations on the same buffer.
2. **Retrieval buffer:** retrieval can often be proceduralized into more specific productions (except failure tests).
3. **Goal buffers:** merging follows more complex rules.
4. **Safety:** compiled production should not generate a result the originals could not generate.
5. **Parameter setting:** learned productions inherit/derive experience, success/failure, and effort estimates.

Examples cited include learning inflection, air-traffic-control skills, paired associates from instructions, anti-air-warfare coordination, and fan-effect learning.

Important: these examples can involve several learning forms at once:

- new chunks
- new productions
- activation learning
- utility learning

---

## 16. Brain / fMRI connection

ACT-R is also used to connect model activity to brain-imaging predictions.

Example in lecture: activity of the **retrieval buffer** during equation solving is used to predict BOLD response in left dorsolateral prefrontal cortex.

The detailed trace for solving `5x + 3 = 18` shows a sequence of visual-attention operations, encodings, memory retrievals, production firings, and finally a motor key press. This illustrates why ACT-R is useful for making **time-resolved** predictions rather than only predicting the final answer.

---

## 17. Models / exercises used in the tutorial

Interactive sessions mentioned:

- Addition model
- Counting model
- a model using perceptual-motor buffers
- build Dialing model
- Sternberg model
- Building Sticks model

These seem to progress from basic knowledge representation and productions toward perception/motor interaction, subsymbolic retrieval, utility, and learning.

---

## 18. Current directions (as presented in the tutorial)

ACT-R 6.0 design goals:

- more modular
- consistent/uniform syntax
- consistent treatment of buffers
- parameter simplification
- model behavior in more complex real-world environments

---

# Quick exam/revision sheet

## Core vocabulary

**Cognitive architecture** - stable infrastructure/mechanisms used to build cognitive models across tasks.

**Chunk** - unit of declarative knowledge, structured by type + slots.

**Production** - condition-action rule representing procedural knowledge.

**Buffer** - interface holding information through which productions communicate with modules.

**Goal buffer** - current task state / focus of internal attention.

**Retrieval buffer** - result of declarative-memory retrieval.

**Conflict set** - productions whose conditions currently match.

**Utility** - value used to choose among competing productions; related to expected benefit/success and cost.

**Activation** - determines availability, probability, and latency of chunk retrieval.

**Base-level activation** - context-independent usefulness based largely on frequency and recency.

**Source activation** - activation coming from current context/goal elements.

**Partial matching** - allows retrieval of imperfectly matching chunks depending on mismatch penalty and similarity.

**Production compilation** - learning mechanism that creates more efficient/specific productions from experience.

## The ACT-R loop to remember

```text
Environment
   ↓
Perceptual modules → buffers
   ↓
Productions match buffer contents
   ↓
Conflict resolution / utility chooses one
   ↓
Production fires
   ↓
Buffers/modules change → retrieval or action
   ↓
Environment changes
   ↺
```

## Most important distinction

```text
DECLARATIVE                         PROCEDURAL
what is known                       how to do something
chunks                              productions
retrieval                           rule firing
activation affects retrieval        utility affects selection
```

## One-sentence summary

**ACT-R models cognition as a modular system in which production rules operate serially over buffer contents, while subsymbolic activation and utility mechanisms use experience, context, costs, and noise to determine what is retrieved, what action is selected, and how long cognition takes.**

---

## Things I would star in my notebook

- **Chunks = declarative; productions = procedural.**
- **Modules communicate with cognition through buffers.**
- Production cycle: **match -> conflict set -> select -> fire -> update buffers -> repeat.**
- **Activation controls memory retrieval; utility controls production choice.**
- Frequency + recency are central to base-level memory activation.
- ACT-R includes perception + motor behavior, not just abstract reasoning.
- Learning happens at both symbolic and subsymbolic levels.
- Timing matters: ACT-R aims to predict *how behavior unfolds in time*, not just whether an answer is correct.
