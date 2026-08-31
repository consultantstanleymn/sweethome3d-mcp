# Notice: Provenance of file-format documentation

This project (`sweethome3d-mcp`) is original, independently-written Python code
released under the MIT License (see `LICENSE`). It is **not** a fork, port, or
derivative of Sweet Home 3D's source code, and it does not bundle, link
against, or redistribute any Sweet Home 3D code or binaries.

Sweet Home 3D itself (https://www.sweethome3d.com) is licensed under the
**GNU General Public License**. To understand the `.sh3d` / `Home.xml` file
format well enough to write a compatible file, the author read:

- Sweet Home 3D's published `SweetHome3D.dtd`.
- A GPL-licensed 2017 mirror of Sweet Home 3D's Java source, specifically the
  classes that read and write `Home.xml`
  (`HomeXMLHandler`, `HomeXMLExporter`, `DefaultHomeInputStream`, and related
  classes).

`docs/SCHEMA.md` in this repository documents **facts about the file format**
extracted from that source (element names, attribute names, defaults,
coordinate conventions, etc.). No GPL source code, comments, or original prose
were copied into this repository — the schema documentation is the author's
own independent write-up of the format, in the author's own words, in the
same way a compatible reader/writer for any file format is commonly built by
studying an existing implementation.

If you are a Sweet Home 3D maintainer or contributor and believe any part of
this repository's documentation is closer to a copy of GPL-licensed
expression than to an independent factual description of the format, please
open an issue — this project's intent is full compliance and good-faith
attribution, not appropriation of GPL work.

## Why MIT and not GPL

File formats and their technical facts (attribute names, defaults, structural
rules) are generally not themselves copyrightable — copyright protects the
original expression of an idea, not the idea or facts about a format. This is
the same legal basis that allows independent, compatible readers/writers to
exist for many proprietary and open file formats without inheriting the
license of the original application. This project follows that same pattern.

This is not a legal opinion and nothing here should be relied upon as legal
advice. If you plan to redistribute or build on this project in a context
where that distinction matters to you, consult your own counsel.
