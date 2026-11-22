-- Puts a research post's papers in a "Read the papers" box at the very top of
-- the post, right under the headline, so someone who searches for a paper's
-- title lands on a page where the paper is one click away.
--
-- It reads the same `papers:` list in the post's front matter that the
-- Research index already shows under each entry, so there is nothing extra to
-- fill in: add a paper there and it appears in both places. An entry without
-- a `url:` is shown as plain text. A post with no `papers:` gets no box.
--
-- Wired up in research/_metadata.yml.

local function as_inlines(value)
  if value == nil then return nil end
  if pandoc.utils.type(value) == "string" then
    return pandoc.Inlines(value)
  end
  return pandoc.Inlines(value)
end

function Pandoc(doc)
  local papers = doc.meta.papers
  if papers == nil or #papers == 0 then
    return doc
  end

  local items = {}
  for _, paper in ipairs(papers) do
    local cite = as_inlines(paper.cite)
    if cite ~= nil and #cite > 0 then
      local line = cite
      if paper.url ~= nil then
        line = pandoc.Inlines { pandoc.Link(cite, pandoc.utils.stringify(paper.url)) }
      end
      table.insert(items, { pandoc.Plain(line) })
    end
  end
  if #items == 0 then
    return doc
  end

  local heading = (#items == 1) and "Read the paper" or "Read the papers"
  local box = pandoc.Div({
    pandoc.Para({ pandoc.Span(pandoc.Inlines(heading), { class = "post-papers-title" }) }),
    pandoc.BulletList(items),
  }, { class = "post-papers" })

  doc.blocks:insert(1, box)
  return doc
end
