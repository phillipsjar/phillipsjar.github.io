-- Adds a "Comments or suggestions?" box to the end of every FAQ page, so
-- each FAQ gets it automatically, including ones published later.
-- An FAQ page is any education/faq-*.qmd file. Wired up in
-- education/_metadata.yml.

local function is_faq()
  local f = (quarto and quarto.doc and quarto.doc.input_file) or ""
  return f:match("[/\\]faq%-[^/\\]*%.qmd$") ~= nil
end

function Pandoc(doc)
  if not is_faq() then
    return doc
  end
  local md = "::: {.faq-feedback}\n" ..
             "**Comments or suggestions?** Please [reach out](../contact.qmd) and let me know!\n" ..
             ":::\n"
  for _, block in ipairs(pandoc.read(md, "markdown").blocks) do
    doc.blocks:insert(block)
  end
  return doc
end
