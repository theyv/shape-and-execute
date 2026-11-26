# Setup guide text (owner-approved draft for AMEND-3)

The agent shows this in the conversation language before the first setup proposal.

```
### Task
- A task holds one or more goals that you state in its intent.
- It is split into jobs. A job is usually one objective that an
  agent can finish within one context window.

### Phases
A task goes through four phases:
> research, planning, execution, review

### Levels
Each phase has a level:
> economy, balanced or premium
Economy saves tokens. Premium buys quality.
The levels start from your defaults. You can change them for
each task; the agent asks about them while it shapes the task.

### Difficulties
Each job has a difficulty:
> mechanical, easy, normal or hard
The agent sets it when it plans the task.
Planning and review use only normal and hard.

## Model routing tables
- You can use different models for different difficulties.
- You can set a MODEL+EFFORT (cell) for every LEVEL (row)
  x DIFFICULTY (column), grouped by PHASE. You can edit the
  tables later in the GUI.
- Projects and tasks inherit the global tables. You can
  change them later per project or per task.

#### Two ways to set model routing
- Tiers mode (default, simpler): four named steps, L1 to L4,
  each one model + effort. A cell only points to a step.
  Change a step once, and every cell that points to it
  follows.
- Free mode: each cell has its own model + effort. Use it
  when four steps are too coarse and you want finer control.
- Tiers mode and Free mode are independent. Switch between
  them any time; a change in one never affects the other.
  Free mode starts as a copy of your tiers.

### Changing settings later
- You can change every setting in the GUI, or ask the agent
  to change it for you.
- Tip: phases can use different levels, for example "plan on
  premium, execute on economy." The next dispatch uses the
  change.
```
