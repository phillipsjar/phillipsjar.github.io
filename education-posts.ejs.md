<%
/* The "Longer reads" list on the Education page (education.qmd, listing id
   posts), for the pages in education/posts/.

   Same card markup as Quarto's built-in "default" listing (like the Research
   page), plus the post's date above its title (leave it off with
   `hide-date: true`). The "Longer reads" heading
   is only printed once at least one post is published, so the page never
   shows an empty section. It's written as raw HTML because a markdown
   heading inside a listing makes Quarto drop the whole listing. While there
   are no posts, a hidden placeholder sits in the list, because Quarto's
   listing script errors on an empty one. */
%>
<% if (items.length) { %>

```{=html}
<h2 class="education-posts-heading anchored">Longer reads</h2>
```

<% } %>

::: {.list .quarto-listing-default .education-posts}

<% if (!items.length) { %>
```{=html}
<div class="d-none" aria-hidden="true"></div>
```
<% } %>

<% for (const item of items) { %>

::: {.quarto-post .image-right <%= metadataAttrs(item) %>}

```{=html}
<div class="thumbnail"><a href="<%- item.path %>" class="no-external">
<% if (item.image) { %>
<img loading='lazy' src="<%- item.image %>" class="thumbnail-image"<% if (item['image-alt']) { %> alt="<%- item['image-alt'] %>"<% } %>>
<% } %>
</a></div>
```

::: {.body}

<% if (item.date && item['hide-date'] !== true) { %>
<div class="listing-date"><%= item.date %></div>
<% } %>
<h3 class="no-anchor listing-title"><a href="<%- item.path %>" class="no-external"><%= item.title %></a></h3>
<% if (item.subtitle) { %>
<div class="listing-subtitle"><a href="<%- item.path %>" class="no-external"><%= item.subtitle %></a></div>
<% } %>

<% if (item.description) { %>

```{=html}
<div class="delink listing-description"><a href="<%- item.path %>" class="no-external">
```

<%= item.description %>

```{=html}
</a></div>
```

<% } %>

:::

:::

<% } %>

:::
