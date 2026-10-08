// All user-facing words live here. Domain/API return codes; this maps them to text.
// Tone rules: experiments not dares, no shame, no streak guilt.

export const copy = {
  appName: "Challenge Jar",
  disclaimer:
    "Everyday practice for social confidence. This is homework, not therapy or medical treatment. " +
    "If anxiety is seriously getting in the way of your life, talk to your GP or an NHS Talking Therapies service.",

  nav: { today: "Today", progress: "Progress", you: "You" },

  tiers: { 1: "Tiny", 2: "Easy", 3: "Medium", 4: "Stretch" },
  tierLabel: (t) => `Tier ${t} · ${copy.tiers[t]}`,
  tierProgress: (n, needed, next) => `${n} of ${needed} full completions to unlock Tier ${next}`,
  tierMax: "Top tier. Keep collecting data.",
  tierHigherUnlocked: (t) => `Tier ${t} is unlocked. Move up under “You” when ready.`,

  categories: {
    stranger: "Stranger micro-contact",
    service: "Service staff",
    peer: "Peer small-talk",
    work_voice: "Work / meeting voice",
    disagreement: "Disagreement",
    hosting: "Hosting",
    phone_voice: "Phone / voice",
    networking: "Networking",
  },

  completion: { full: "Did it", partial: "Partly", none: "Didn't this time" },

  suds: {
    scale: "0 = totally calm · 100 = the most anxious you can imagine",
    target: (n) => `~${n} SUDs`,
  },

  week: {
    score: (s, t) => `${s} of ${t} this week`,
    freezesLeft: (n) => (n === 1 ? "1 freeze left this month" : `${n} freezes left this month`),
  },

  today: {
    heading: "Today's experiment",
    welcomeBack: "Welcome back. No catching up needed, just today's one.",
    pickPrompt: "Pick one. They're all the same size.",
    drop: "Drop this safety behaviour",
    success: "Counts as done when",
    easierToggle: (t) => `Low-energy day? Show Tier ${t} options instead`,
    normalToggle: "Back to my tier",
    ifThenTitle: "Make it an if–then plan",
    when: "If it's…",
    whenPlaceholder: "e.g. after the 9am stand-up",
    where: "and I'm at…",
    wherePlaceholder: "e.g. the café by Hitchin station",
    then: "then I'll:",
    predicted: "How anxious do you expect to feel?",
    feared: "What are you afraid will happen? (optional)",
    fearedPlaceholder: "e.g. they'll look at me like I'm weird",
    commit: "Commit to it",
    cancel: "Back",
    planLine: (when, where) => `If it's ${when} and I'm at ${where}, then I'll:`,
    logIt: "Log how it went",
    changePick: "Change pick",
    predictedWas: (n) => `You predicted ${n}`,
    fearWas: (f) => `Feared: “${f}”`,
    freezeBtn: "Busy day? Use a freeze",
    frozen: "Today is frozen. Rest is part of the plan.",
    pendingTitle: (d) => `Your plan from ${d} isn't logged yet`,
    done: "That's today done. See you tomorrow.",
  },

  evening: {
    title: "How did it go?",
    howFar: "Did you do it?",
    actual: "How anxious did you actually feel at the peak?",
    predictedLate: "Looking back, what did you expect beforehand?",
    dropped: (trap) => `Did you drop the safety behaviour? (${trap})`,
    yes: "Yes",
    no: "No",
    note: "One line: what actually happened?",
    notePlaceholder: "e.g. she smiled and said the flat white is the best one",
    save: "Save",
  },

  result: {
    easier: (p, a, g) => `You predicted ${p}, it was ${a}. ${g} points easier than your brain forecast.`,
    same: (p) => `Predicted ${p}, felt ${p}. Spot-on forecast.`,
    harder: (p, a) => `Predicted ${p}, felt ${a}. Harder than expected, and you still did it. That counts.`,
    noPrediction: "Logged. Add a prediction next time to see the gap.",
    none: "Logged. Not doing it is data too: what got in the way? Tomorrow's card is just as small.",
    partial: "Partial counts as an approach. You showed up.",
  },

  events: {
    tier_unlocked: (t) => `Tier ${t} unlocked. Your cards move up from tomorrow. You can step back down any time under “You”.`,
    comeback: "Comeback. Returning after a gap is the skill that actually matters.",
    title: (name) => `New title: ${name}`,
  },

  titles: {
    rookie_nod: { name: "Rookie Nod", hint: "Your first approach" },
    brief_eye_contact: { name: "Brief Eye Contact", hint: "5 approaches" },
    one_sentence_out: { name: "One Sentence Out", hint: "10 approaches" },
    barista_banter: { name: "Barista Banter", hint: "3 service-staff challenges done fully" },
    meeting_voice: { name: "Meeting Voice", hint: "3 work/meeting voice challenges done fully" },
    cold_open: { name: "Cold Open", hint: "A Tier 3+ stranger or networking opener" },
    held_disagreement: { name: "Held Disagreement", hint: "A Tier 2+ disagreement done fully" },
    hosted_the_table: { name: "Hosted the Table", hint: "A Tier 3+ hosting challenge" },
    safety_dropper: { name: "Safety Dropper", hint: "Drop the safety behaviour 10 times" },
    comeback_kid: { name: "Comeback Kid", hint: "Come back after 3+ days away" },
  },

  progress: {
    heading: "Progress",
    thisWeek: "This week",
    fullPct: "Full completions",
    approaches: "Approaches",
    dropped: "Safety behaviours dropped",
    chartApproaches: "Approaches per week",
    chartGap: "Average prediction gap (expected − actual)",
    chartGapNote: "Above 0 = it was easier than you feared. Drifting toward 0 = your forecasts are getting more accurate.",
    target: (t) => `target ${t}`,
    tooltipWeek: (d) => `Week of ${d}`,
    tooltipApproaches: (n) => `${n} approach${n === 1 ? "" : "es"}`,
    tooltipGap: (g) => (g === null ? "No gap data" : `Gap ${g > 0 ? "+" : ""}${g}`),
    showTable: "Show as table",
    hideTable: "Show chart",
    tableHead: ["Week of", "Approaches", "Full", "Freezes", "Avg gap"],
    byTier: "Prediction gap by tier",
    byTierHead: ["Tier", "Logged", "Earlier", "Recent"],
    byTierEmpty: "Log a few experiments with predictions to see this.",
    history: "Recent experiments",
    historyEmpty: "Nothing logged yet. Today's the first data point.",
    notLogged: "not logged",
  },

  you: {
    titles: "Titles",
    earned: (d) => `Earned ${d}`,
    tierHeading: "Your tier",
    tierHelp: "You can step down any time. You can't jump up past what you've unlocked: the ladder is the point.",
    about: "About",
  },

  errors: {
    already_picked: "You've already picked today's experiment.",
    not_offered: "That card isn't on offer today.",
    cannot_unpick: "That plan can't be changed now.",
    outside_log_window: "That plan is too old to log now. Fresh start today.",
    actual_suds_required: "Rate how anxious you actually felt.",
    freeze_future: "You can't freeze a future day.",
    freeze_outside_week: "Freezes only cover days this week.",
    freeze_already_frozen: "That day is already frozen.",
    freeze_day_has_approach: "You already did something that day. No freeze needed.",
    freeze_none_left: "No freezes left this month.",
    tier_locked: "That tier isn't unlocked yet.",
    not_found: "Not found.",
    generic: "Something went wrong. Try again.",
  },
};
