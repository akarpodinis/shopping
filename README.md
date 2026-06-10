# Shopping

My wife and I love to cook together, we've been doing this daily since we got our first place back in the day.  We noticed over time that we had a pretty regular menu in rotation, with some variation, which we would talk about in shorthand and would have to translate into a shopping list pretty often.  We'd inevitably miss ingredients because we were rushing or assumed we remembered everything we needed or we would forget to check our usual stock of ingredients for something and not pick it up from the store.  Little annoyances here and there adding up over time.

There's gotta be a better way, right?

Well, I have the skills to get to that better way, so why not do it?  About the time I started to need to write more intensive database queries for work I started working through what a query would look like to get all ingredients associated with a given recipe.  The obvious and useful features fell into place after that:

* Manage a list of recipes and their ingredients
* Create a shopping list from recipes, organized by store aisle
* Keep track of which ingredients we have stocked and optionally add them to the next list if we need more

I wrapped all of this into a nice web app, learning HTML and CSS on the way (including responsive features of CSS so we can use the app on our phones while in the grocery store), choosing clear fonts and a simple color scheme to tie it all together.  I've merged over one hundred PRs since then, expanding on its features, but the core behavior remains the same, and we use this software biweekly for our shopping trips.  I have GitHub actions automatically deploying tagged releases to fly.io, so the process is as seamless as it could be; I make a branch, make some narrow changes to add a new feature, test it locally, merge and tag and push and our latest software is available on the public internet in minutes.
