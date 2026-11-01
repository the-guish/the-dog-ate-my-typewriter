---
title: "my dear box"
date: 2026-11-01
tags: [application-architecture]
---

Why humankind likes boxes so much? There is a reason, and it is old. When people started making tools, we made arrowheads, fishhooks, and little figures of the divinities we had. We were nomads, so we carried them. At the beginning, I imagine, in bags.

Bags matter too. They are important, and useful. Over time they gave way to boxes, above all in modern times, or from the point we could do carpentry. That has been a constant through the whole of human history. We have every kind of box. The ones shaped like a rectangular prism are the popular ones, and they run from a cardboard shoebox to a steel safe, or a shipping container that spends years crossing the ocean.

What is so captivating about a box?

Humans like things. We like making them, having them, trading them, and giving them away. Boxes help us organize those things. Without boxes, our things would probably sit in one large room, which, by the way, is also a box. Houses are boxes that contain rooms shaped like boxes. It is impossible to think of any kind of organization without boxes, and Marie Kondo could tell you the same.

## Labels for a finite mind

Organizing helps because the mind is finite. We like having many things, and we cannot keep a record of that many things at once. While someone, after long practice, can recite [79 digits](https://www.science.org/doi/10.1126/science.7375930), most of us cannot remember more than [about seven](https://labs.la.utexas.edu/gilden/files/2016/04/MagicNumberSeven-Miller1956.pdf) or [four](https://doi.org/10.1017/S0140525X01003922) items on a supermarket list. I never get to whatever came after "butter".

That's where boxes get interesting. If I have a hundred things to remember, where are they? I can have ten boxes of ten, and a label on each box. My mind can then find, with less effort, where each of those hundred things is when I need it. That is the great function of a box.

Large warehouses work the same way. Goods go into small boxes, then into larger containers, then into aisles, then into whole sheds, and sometimes into separate buildings: one property in one city with four sheds, another property in another city with seven. All of that has to live in an inventory system. A logistics company could not survive without boxes, smaller boxes, and larger boxes, one inside another.

There is no way to run a large project without a structure, and without a plan for how those boxes are organized. If you have ever moved house, you have a sense of what it takes. You put everything into boxes, you move, and then you entertain yourself searching for your things inside those boxes. A house move is the smallest version of a complex project. Most logistics work is thousands or millions of times that, and it needs much more advanced schemes.

In one of my past lives, I was an Oracle Applications implementer, working on ERP and supply chain. The Oracle SCM suite is an interesting system: it runs from handheld barcode scanners on the warehouse floor to Bayesian forecasting algorithms, and I saw it up close letting large companies achieve milestones like [tracking inventory across many countries and forecasting material requirements](https://www.slideshare.net/slideshow/zero-downtime-for-oracle-ebusiness-suite-on-oracle-exalogic/40254433), down to the individual shelf.

Behind much of it sits a key domain entity: a "containers" table with a parent ID. Experts like Fede Elicetche know it by its official name, WMS_LICENSE_PLATE_NUMBERS.

For today, just know that each record is something that can sit inside something else: a box on a pallet, a pallet in a shipping container, all of them tagged.

Some key tables and fields turns millions of loose items into a hierarchy. Move a pallet, and everything on it moves in one step.

Never underestimate a well-modeled box.

## The warehouse in your code

Back in our more ethereal world, swap pallets for modules and warehouses for codebases, and the problem barely changes.

Our mind is the same. It is the mind of that prehistoric person carrying arrowheads and fishhooks in a bag, the mind that organizes a move, and the mind that organizes a project of thousands of lines of code. Same mind, same capacities, same structures.

In software we have to think in boxes. That is why we have modules, folders, libraries, and components. Each one is a box we can give a meaning, and we know roughly what is inside. That is what takes us from a need, such as "I need to find my drill for this," to actually having the drill in hand.

A codebase works the same way. I need to know where the price gets recorded at the moment the user places the order. Where is that? I need a short series of boxes, three to ten of them: the modules of the system. I open one, find the boxes inside, and say: the prices ought to be in the large orders box; inside orders, at the moment of booking; inside booking, in the prices part. I open that box and I may be looking at some hundreds of lines I still have to scan. The structure of the boxes is what gets me there in three jumps, from the need to the code that matters.

That is the point of a box. We have a finite mind, and we like having many things. We used to collect clay figurines; now we collect interfaces that hide three modules: one making HTTP calls, another writing files, the last talking to a database. Software architecture is finding the boxes for the things we collect today.

## Why splitting still matters

Why do boxes still matter, if an AI can do the work? Maybe one day they won't. That day might come next week, in two years, in two centuries, or never: a day when nobody thinks about code anymore, and the whole system is one gigantic black box behind a voice interface. You say, "God of the AI, orders from tier-2 customers have to show up in next year's pricing policy," and nobody touches anything else.

We are not there yet. As of late 2026, the strongest models available to consumers and regular companies have context windows of about a million tokens, and they [work best well below that limit](https://www.trychroma.com/research/context-rot). A large codebase doesn't fit in a single call. We top out at four to seven items; models handle far more. But their capacity is still finite.

Nobody has settled on a general, absolute way to work across millions of lines of code. So those millions of lines still have to be organized to fit the context window of the models, and the "context window" of humans.

Software architecture is the answer to that, and it means discovering or designing the large boxes, with the medium boxes and the small boxes, and putting the lines of code inside them, so a person can know where each thing lives, and so a model can work on a part of the system by mapping a requirement straight onto those boxes.

Take the requirement from before: change the pricing policy for tier-2 customers, in a two-line prompt. Without boxes, the model has to scan thousands of lines written in different patterns, which wastes time and money and produces suboptimal results.

With boxes, it finds the right box, opens it, and reads what it needs. That takes the model seconds. For people, the gain is similar: minutes to answer if they know the code, hours to onboard instead of days if they don’t.

## What is better than a black box or a glassbox?

A black box usually means something whose inside we do not know: we see what happens outside, and not what happens inside. A glass box, a box of glass, a transparent one, is something we understand completely. 


These days I hear a lot of programmers ask, "why would I review anything, if the AI already knows how to do it all, or the AI can review itself?". That posture, in its more pure version, treats the software artifact as a black box. We do not know how is it built inside we only care about how it behaves and interacts with the rest of the world. That I consider a valid strategy in many cases.


On another end, it is also posible pursue a glass-box approach, closer to what was assumed as normal in pre-AI era, we actually review the code and approve when we get to a reasonable level of shared understanding according to some criteria, many times tacit.
In this second approach, the throughput would be less, the ability of the humans to maintain and support the system would be higher.
And it is a valid strategy in many cases.


How much to review the code is the same formula of before, and it is dependent on which position you take in terms of expected throughput, technical debt and investment in tooling and architechture beforehand.

If you accept "classic" throughput, in terms of your team, a full glass-box policy would work. And my personal stance is that is still valid for selected pieces of the system where we want to keep a strong grip.

If you favor throughtput, black boxes need to appear, and that is ok. You do not have to review, if you do not want to, what is inside the smaller boxes. But you will be more efficient and keep the throughput for longer time if you know where to find them with confidence.

You do have to take part in designing the structure of the boxes. That is how you keep doing the work that falls to you in the times we are in: step in on the particular matters that count, coordinate, and also design and assist the AI's flows, so the AI can map requirements onto those boxes, work more efficiently and more effectively, and at the same time generate fewer problems that you have to review.

On the contrary a succession of "I asked for something, I skim at my best will a small part of it, I merge" produces one thing: a gigantic black box. Coding and merging without a structure is what produces a large black box.

For the volume of code we handle now, hoping for a glass box would not meet the business expectations at most of the organizations. Going full black will find limits as the system grows.

So the strategy is not one large black box, and it is not a glass box either.

The answer is a glass box with small black boxes inside. You will have many black boxes, three hundred to five thousand lines of code at most, depending on the threshold you choose to set. You do not have to review those black boxes. Because they interact with each other, every one of them has to sit inside a glass box that you do understand, where you know how each part connects to the next.

The absolute, total answer to all of those questions people ask about this is: a glass box of black boxes.
