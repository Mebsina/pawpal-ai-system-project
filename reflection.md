# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
   - The design models a pet care scheduling system using five classes. An `Owner` manages multiple `Pet` objects, each pet owns its own list of `Task` objects, and a `Scheduler` retrieves all tasks across the owner's pets, fits them within the time budget, and returns a `Schedule`.

- What classes did you include, and what responsibilities did you assign to each?
   - **Owner**: holds the owner's name, daily time budget (`available_minutes`), optional preferences, and a list of pets. It is the primary constraint that drives scheduling.
   - **Pet**: stores the pet's name, species, age, special needs, and owns its list of care tasks.
   - **Task**: represents a single care activity with a title, duration, priority (low, medium, or high), category, frequency, completion status, and optional notes.
   - **Schedule**: the output of planning. Holds two lists: tasks that fit within the time budget, and tasks that did not. A pure data container with no logic.
   - **Scheduler**: the core engine. Takes an `Owner`, retrieves tasks across all pets, and exposes `generate_plan()`, which sorts tasks by priority and fits them within the time budget, and `explain_plan()`, which narrates why each task was included or excluded.

**b. Design changes**

- Did your design change during implementation?
   - Yes.

- If yes, describe at least one change and why you made it.
   - The `Task` class stores priority as a string (`"low"`, `"medium"`, `"high"`), but `generate_plan()` needs to sort tasks by priority. Since strings cannot be sorted numerically, a `PRIORITY_ORDER` mapping (`{"low": 1, "medium": 2, "high": 3}`) was added to convert it to an integer for sorting inside `generate_plan()`. The `Task` class itself stays unchanged.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
   - The scheduler considers two constraints: the owner's daily time budget (`available_minutes`) and each task's priority level (low, medium, or high). Tasks are sorted by priority first, then by duration as a tiebreaker when two tasks share the same priority.

- How did you decide which constraints mattered most?
   - Time is the hard constraint - the scheduler never exceeds `available_minutes`. Priority determines the order tasks are considered, so high-priority tasks are always evaluated before lower-priority ones. This ensures the most important tasks get scheduled first when time is limited.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
   - The scheduler uses a greedy approach: it processes tasks in priority order and skips any task that does not fit in the remaining time, even if a smaller lower-priority task could still fit. For example, if a high-priority 45-minute task cannot fit, the scheduler moves it to unscheduled and continues - it does not go back to try fitting it later after smaller tasks are added.

- Why is that tradeoff reasonable for this scenario?
   - For a daily pet care routine, simplicity and predictability matter more than perfect optimization. The greedy approach is easy to understand and explain to the user, and the tiebreaker (shortest task first within the same priority) already helps pack more tasks into the schedule.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
