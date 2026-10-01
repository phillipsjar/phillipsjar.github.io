<%
/* The Research page's listing (used by research.qmd via `template:`).

   It reproduces the markup of Quarto's built-in "default" listing
   (share/projects/website/listing/item-default.ejs.md in Quarto 1.10), so
   each entry looks the same as it did with `type: default`, with two
   changes:
     - the list carries a .research-listing class, so CSS can target the
       Research page without touching the Education page's listing;
     - each entry is wrapped in a .research-entry block, and if the post's
       front matter has a `papers:` list, it is shown under the whole entry
       (picture and text) as "Relevant research papers".

   A `papers:` entry looks like this; leave `url` out for a paper with no
   link yet (it is then shown as plain text):

     papers:
       - cite: "Phillips, JR and MC Womack. (2025). Title. *Journal*."
         url: "https://..."

   Shows image, title, subtitle and description, the same fields research.qmd
   used to ask for. */
%>
::: {.list .quarto-listing-default .research-listing}

<% for (const item of items) { %>

::: {.research-entry <%= metadataAttrs(item) %>}

::: {.quarto-post .image-right}

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

:::

::: {.metadata}

```{=html}
<a href="<%- item.path %>" class="no-external">
</a>
```

:::

:::

<%
if (Array.isArray(item.papers) && item.papers.length) {
  const lines = item.papers.map(p =>
    "- " + (p.url ? "[" + p.cite + "](" + p.url + ")" : p.cite));
  print("\n::: {.listing-papers}\n\n" +
        "[Relevant research papers]{.listing-papers-title}\n\n" +
        lines.join("\n") + "\n\n:::\n");
}
%>

:::

<% } %>

:::
