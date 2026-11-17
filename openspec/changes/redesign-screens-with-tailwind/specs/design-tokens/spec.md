# Spec Delta

## Purpose
Keeps the site's look in one place: a single token file that every page's colours, fonts, type sizes and corner radii come from, so the site can be restyled by editing that file alone.

## ADDED Requirements

### Requirement: One token file holds the site's look
The site's colours, font families, type sizes, letter spacing, line heights, corner radii, breakpoints and container widths SHALL be defined in one token file. It SHALL define a named role for each job a value does on the site: the page ground, surfaces, ink, icons, body text, quiet text, rules, control borders, links, the accent and the type on it, the map's ground, water, parks, pins and location dot, the display, body and label fonts, and the tile, box, control and pill radii.

#### Scenario: The roles exist
- **WHEN** the token file is read
- **THEN** it defines every role named above, each with a value

#### Scenario: The accent as designed
- **WHEN** the site is built from the token file as shipped
- **THEN** the accent is `#FFEF3B`, links are the blue scale's 600 step, the display font is Inter Tight, the body font is the system's sans and the label font is Geist Mono

### Requirement: Changing a token restyles every page
A page's styles SHALL take a role's value from the token file, so that changing one role's value and rebuilding the stylesheet changes it wherever that role is used, with no template edited.

#### Scenario: A new accent
- **WHEN** the accent role is changed to `#FF6B00` and the stylesheet is rebuilt
- **THEN** the header's search button, a "Tonight" tag and the band page's next-show band are all drawn in `#FF6B00`

#### Scenario: A new display font
- **WHEN** the display font role is changed to "Georgia" and the stylesheet is rebuilt
- **THEN** the site's name in the header and a page's heading are set in Georgia

### Requirement: Pages use roles, never literal values
Public page templates and the site's own stylesheets, other than the token file, SHALL NOT contain a literal colour (hex, `rgb`, `hsl` or `oklch`), a literal font family, or a class naming a step of a colour scale. Icons drawn in a template SHALL take their colour from the text colour or a role. The admin's templates and the email digest's HTML are outside this rule.

#### Scenario: A literal colour is caught
- **WHEN** a public template contains `#8b5b8b` or a class such as `bg-[#8b5b8b]` or `text-gray-700`
- **THEN** the automated check fails and names the file and the value

#### Scenario: The shipped templates pass
- **WHEN** the check runs over the public templates and stylesheets as shipped
- **THEN** it finds nothing

### Requirement: Fonts and styles are served by the site
Every stylesheet and font file a public page uses SHALL be served from the site's own static files. A page SHALL NOT request a stylesheet or font from another site.

#### Scenario: No outside font or stylesheet
- **WHEN** a visitor opens the home page
- **THEN** every stylesheet and font request goes to the site's own address
