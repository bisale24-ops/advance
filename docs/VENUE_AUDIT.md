# Venue audit

Top room of each brief, 5 headliners x 3 cities. Passes all three checks: 12 of 15.

| headliner | city | top room | city in address | site | mentions shows | address |
|---|---|---|---|---|---|---|
| Phoebe Bridgers | Chicago | The Chicago Theatre | yes | 200 | yes | 175 N State St Chicago, IL 60601 |
| Phoebe Bridgers | Denver | Bluebird Theater | yes | 200 | yes | 3317 E Colfax Ave Denver, CO 80206 |
| Phoebe Bridgers | Nashville | The Blue Room | yes | 200 | yes | 623 7th Ave S Nashville, TN 37203 |
| Mitski | Chicago | The Riviera Theatre | yes | 200 | NO | 4746 N Racine Ave Chicago, IL 60640 |
| Mitski | Denver | Bluebird Theater | yes | 200 | yes | 3317 E Colfax Ave Denver, CO 80206 |
| Mitski | Nashville | The Blue Room | yes | 200 | yes | 623 7th Ave S Nashville, TN 37203 |
| Fontaines D.C. | Chicago | The Empty Bottle | yes | 200 | yes | 1035 N Western Ave Chicago, IL 60622 |
| Fontaines D.C. | Denver | Hi-Dive | yes | 200 | yes | 7 S Broadway Denver, CO 80223 |
| Fontaines D.C. | Nashville | The Blue Room | yes | 200 | yes | 623 7th Ave S Nashville, TN 37203 |
| Chappell Roan | Chicago | The Chicago Theatre | yes | 200 | yes | 175 N State St Chicago, IL 60601 |
| Chappell Roan | Denver | Denver Art Society | yes | 200 | yes | 734 Santa Fe Dr Denver, CO 80204 |
| Chappell Roan | Nashville | The Blue Room | yes | 200 | yes | 623 7th Ave S Nashville, TN 37203 |
| Noah Kahan | Chicago | United Center | yes | HTTPError | NO | 1901 W Madison St Chicago, IL 60612 |
| Noah Kahan | Denver | Your Mom's House Denver | yes | 200 | yes | 608 E 13th Ave Denver, CO 80203 |
| Noah Kahan | Nashville | Marathon Music Works | yes | 200 | NO | 1402 Clinton St Nashville, TN 37203 |

A failure means the check could not confirm it (a site that blocks scripts also fails); it is listed, not removed.
Not checked: capacity, availability, whether the room suits the headliner's draw.

## What the three failures are, and what the audit does not clear

- United Center: its site refuses scripted requests (HTTPError), so the check could not run; it is a major arena, not a false venue.
- The Riviera Theatre and Marathon Music Works: the fetched home page has no show wording in the first 400 KB the script reads (their listings load by script). Both are working concert rooms, so this is a limit of the check, not a finding against them.
- Left as failures on purpose: the script did not get to say yes.

Two things the table shows that are not flattering:
- **Little difference between artists in smaller markets.** The Blue Room tops Nashville for four of the five headliners, Bluebird Theater tops Denver for two. Qloo's place ranking leans on the room's overall standing in a city more than on a particular act, so for a mid-size city the room list is closer to a good shortlist for any indie act than a per-artist answer.
- **A gallery in the list.** Denver Art Society ranks first for Chappell Roan. It hosts events, so it passes the check, but it is an art space, not a touring room; the category filter keeps galleries that also tag as live-music venues.

Not checked, and not claimed: capacity, availability, whether a room suits the headliner's draw.
