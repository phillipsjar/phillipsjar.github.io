<%
/* The Research page's listing (used by research.qmd via `template:`).

   It reproduces the markup of Quarto's built-in "default" listing
   (share/projects/website/listing/item-default.ejs.md in Quarto 1.10), so
   the page looks the same as it did with `type: default`, with two changes:
     - the list carries a .research-listing class, so CSS can target the
       Research page without touching the Education page's listing;
     - a post whose front matter has a `paper:` line gets it shown as a
       citation under its blurb.

   Shows image, title, subtitle and description, the same fields research.qmd
   used to ask for. */
%>
::: {.list .quarto-listing-default .research-listing}

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

<% if (item.paper) { %>

::: {.listing-paper}
<%= item.paper %>
:::

<% } %>

:::

::: {.metadata}

```{=html}
<a href="<%- item.path %>" class="no-external">
</a>
```

:::

:::

<% } %>

:::
