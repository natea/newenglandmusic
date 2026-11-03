## ADDED Requirements

### Requirement: Signing up needs only an email address
`/digest` SHALL show a form asking for an email address and for the shows wanted. It SHALL NOT ask for a password or a phone number. A valid submission SHALL create an unconfirmed `Subscriber` with its choices and send one confirmation email holding a signed link, saying who asked and that it can be ignored. An invalid address, or one holding a line break, SHALL show an error and create nothing.

#### Scenario: New address
- **WHEN** a visitor submits a valid address and at least one choice
- **THEN** an unconfirmed subscriber exists with those choices, exactly one confirmation email is sent to that address, and the page says to check the inbox

#### Scenario: Address already signed up
- **WHEN** a visitor submits an address that already has a confirmed subscriber
- **THEN** the page is the same as for a new address, the stored choices are unchanged, and the email sent says the address already has a subscription and how to sign in

#### Scenario: Not an email address
- **WHEN** a visitor submits "not-an-email"
- **THEN** the form shows an error, no subscriber is created, and no email is sent

#### Scenario: Form starts from remembered filter
- **WHEN** a visitor whose remembered filter is Vermont opens `/digest`
- **THEN** the Vermont area choice is already ticked

#### Scenario: Remembered neighborhood narrowing
- **WHEN** a visitor whose remembered filter narrows an area to a neighborhood opens `/digest`
- **THEN** the area choice is ticked without the neighborhood, and the stored choice holds no neighborhood

### Requirement: Signing up again before confirming
A second signup for an address still unconfirmed SHALL send a fresh confirmation and SHALL NOT change the stored choices.

#### Scenario: Second signup
- **WHEN** an unconfirmed address signs up again with different choices
- **THEN** a new confirmation is sent and the first choices stay

### Requirement: Signing up reveals nothing about other addresses
The response to a signup SHALL be the same page whether or not the address already has a subscriber, so the form can't be used to find out who has signed up. For an address that already has a confirmed subscriber, the email sent SHALL say so and say how to sign in, and the stored choices SHALL stay unchanged.

#### Scenario: Same page for both
- **WHEN** one visitor submits a new address and another submits a signed-up address
- **THEN** both see the same page

### Requirement: Confirmation switches the email on
The confirmation link SHALL be signed and SHALL expire after 7 days. Opening it SHALL show a page with a Confirm button and change nothing; submitting the button SHALL mark the subscriber confirmed. It SHALL NOT sign the visitor in. An expired or altered link SHALL change nothing and offer to sign up again. Unconfirmed subscribers older than 7 days SHALL be deleted by the weekly sending command.

#### Scenario: Link then button
- **WHEN** a visitor opens the confirmation link within 7 days and presses Confirm
- **THEN** the subscriber is confirmed, and the visitor is not signed in

#### Scenario: Opening alone changes nothing
- **WHEN** a mail scanner opens the confirmation link without submitting
- **THEN** the subscriber is still unconfirmed

#### Scenario: Altered link
- **WHEN** a visitor opens a confirmation link whose signature was changed
- **THEN** the subscriber stays unconfirmed and the page offers to sign up again

#### Scenario: Old unconfirmed sign-up
- **WHEN** the sending command runs and a subscriber was created 8 days ago and never confirmed
- **THEN** that subscriber is deleted

### Requirement: Choosing which shows
The signup and preferences forms SHALL offer these choices, and a subscriber SHALL need at least one:
- **Area:** a region, state or metro area offered by `event-geo-filter`, optionally narrowed to some of a metro's towns, or "All of the Northeast";
- **Near a place:** a ZIP code or town, resolved with the location form's lookup, and a distance of 5, 10, 25, 50 or 100 miles;
- **Follow:** one or more towns or venues.

#### Scenario: Several kinds together
- **WHEN** a visitor ticks the Vermont area, enters "02143" with 10 miles, and follows one venue
- **THEN** three choices are stored for the subscriber

#### Scenario: Too many choices
- **WHEN** a form holds 21 choices
- **THEN** the form shows an error and stores nothing

#### Scenario: Unknown place
- **WHEN** a visitor enters a ZIP code or town the lookup doesn't know
- **THEN** the form shows an error and stores nothing

#### Scenario: All of the Northeast
- **WHEN** a visitor picks "All of the Northeast"
- **THEN** that is stored as a choice that selects every area

#### Scenario: No choice
- **WHEN** a visitor submits an address with nothing chosen
- **THEN** the form asks for at least one choice and creates nothing

#### Scenario: Place is stored rounded
- **WHEN** a "near a place" choice is saved for ZIP code 02143
- **THEN** the stored coordinates have three decimal places and nothing finer is kept

### Requirement: Limits on choices
A subscriber SHALL have at most 20 choices, and a label at most 100 characters. A "near a place" choice SHALL keep the looked-up ZIP code or town's point, rounded as the location form rounds it, and not a street address.

#### Scenario: Limit
- **WHEN** a form holds 20 choices
- **THEN** it is accepted

### Requirement: Choices that no longer exist
An ambiguous town SHALL make the form ask the visitor to choose, and store nothing until they do. An area or town choice that no longer exists, in whole or in part, SHALL select nothing (never a wider area) and be marked "no longer listed" on the preferences page. A deleted venue SHALL drop out of the choices.

#### Scenario: Shared town name
- **WHEN** a visitor enters a town name that several towns share
- **THEN** the form lists the candidates and stores no choice until one is picked

#### Scenario: Area no longer listed
- **WHEN** a stored area choice names a state that is gone from the offered areas
- **THEN** the preferences page marks it "no longer listed" and the weekly email selects nothing for it

#### Scenario: Area partly gone
- **WHEN** a stored metro-and-towns choice names a metro that is gone, or a town that was renamed
- **THEN** the preferences page marks it "no longer listed" and the weekly email selects nothing for it, not the whole state or metro

#### Scenario: Venue deleted
- **WHEN** a followed venue is deleted
- **THEN** it is no longer among the subscriber's choices

### Requirement: Signing in with an emailed code
`/digest/sign-in` SHALL ask for an email address and send a 6-digit code made with a secure random source, holding only the code and no link. The site SHALL store only a keyed hash of the code. A code SHALL work once and expire after 15 minutes, and asking for a new code SHALL cancel the earlier ones. A correct code SHALL sign the visitor in. The page SHALL respond the same for addresses with no confirmed subscriber and SHALL send them nothing.

#### Scenario: Newer code cancels older
- **WHEN** two codes are requested for one address and the first is entered
- **THEN** it is rejected

#### Scenario: Correct code
- **WHEN** a confirmed subscriber asks for a code and enters it within 15 minutes
- **THEN** they are signed in and see their preferences

#### Scenario: Code used twice
- **WHEN** a code that has already signed someone in is entered again
- **THEN** it is rejected

#### Scenario: Expired code
- **WHEN** a code is entered 16 minutes after it was sent
- **THEN** it is rejected and the page offers to send a new one

#### Scenario: Too many wrong tries on one code
- **WHEN** five wrong codes are entered for one request
- **THEN** the correct code is rejected as well, and a new code must be requested

#### Scenario: Too many wrong tries for one address
- **WHEN** ten wrong codes are entered for one address in an hour, across several requests
- **THEN** sign-in for that address is refused for the rest of the hour

#### Scenario: Unknown address
- **WHEN** someone asks for a code for an address with no confirmed subscriber
- **THEN** the page looks the same as for a known address and no email is sent

#### Scenario: Reply does not wait for the mail service
- **WHEN** a code is requested for a known address and for an unknown address
- **THEN** both replies are sent without waiting for the mail service

### Requirement: Limits on emails to one address or from one client
The site SHALL send at most 3 confirmation, already-subscribed and sign-in code emails to one address in an hour, and SHALL accept at most 10 signup or sign-in requests from one client address in an hour. Over a limit, the page SHALL look the same and send nothing. The signup form SHALL hold a hidden field that people leave empty, and a submission that fills it SHALL create nothing.

#### Scenario: Address limit
- **WHEN** a fourth email of those kinds is requested for one address within an hour
- **THEN** none is sent and the page looks the same

#### Scenario: Client limit
- **WHEN** one client makes an eleventh signup request within an hour
- **THEN** no subscriber is created and no email is sent

#### Scenario: Hidden field filled
- **WHEN** a signup submits the hidden field with text
- **THEN** no subscriber is created and no email is sent

### Requirement: Managing a subscription
A signed-in subscriber SHALL see a preferences page where they can change their choices, pause or resume the weekly email, sign out, and delete the account. Changing choices SHALL need the same validity as signing up. Deleting the account SHALL ask for confirmation, then delete the subscriber, its choices and its codes. Pages that change or show a subscriber SHALL need a signed-in session, checked against the subscriber on every request, and SHALL send the visitor to sign-in otherwise.

#### Scenario: Change choices
- **WHEN** a signed-in subscriber removes the Vermont area and adds a venue
- **THEN** the stored choices are the changed set and the next email uses them

#### Scenario: Pause and resume
- **WHEN** a subscriber pauses the email
- **THEN** no weekly email is sent to them until they resume it

#### Scenario: Delete account
- **WHEN** a subscriber confirms deleting their account
- **THEN** the subscriber, its choices and its sign-in codes no longer exist, and the visitor is signed out

#### Scenario: Not signed in
- **WHEN** a visitor who isn't signed in opens the preferences page
- **THEN** they are sent to the sign-in page

#### Scenario: Not signed in, changing
- **WHEN** a visitor who isn't signed in posts a pause or a delete
- **THEN** nothing changes

#### Scenario: Sign out
- **WHEN** a signed-in subscriber signs out
- **THEN** the session is emptied and the preferences page asks for sign-in

#### Scenario: Deleted subscriber's session
- **WHEN** a subscriber's account is deleted while another browser is signed in as them
- **THEN** that browser is treated as signed out

### Requirement: Sessions and pages are guarded
A page SHALL change something only on a POST with a CSRF token, apart from the one-click unsubscribe post. Signing in SHALL start a fresh session key and last 30 days at most, and SHALL NOT log the visitor in as a Django user. Pages holding tokens or choices SHALL be `noindex`, `no-store` and send no referrer.

#### Scenario: Missing CSRF token
- **WHEN** a signed-in subscriber's pause is posted without a CSRF token
- **THEN** nothing changes

#### Scenario: Session after sign-in
- **WHEN** a subscriber signs in
- **THEN** the session key differs from before, and no Django user is logged in

#### Scenario: Page headers
- **WHEN** the preferences page is fetched
- **THEN** it carries `noindex`, `no-store` and no-referrer headers

### Requirement: One-click unsubscribe
Every email SHALL carry an unsubscribe link signed by the site, which never expires, and the `List-Unsubscribe` and `List-Unsubscribe-Post` headers for the same address. Opening the link SHALL show a page with an unsubscribe button and a masked address, and change nothing; submitting it, or a mail client's one-click post (which carries no CSRF token), SHALL pause the email at once without signing in. A link with an altered signature SHALL change nothing. The page SHALL say how to resume.

#### Scenario: Link then button
- **WHEN** a subscriber opens the unsubscribe link and presses the button
- **THEN** the subscriber is paused and the page says so

#### Scenario: Opening alone changes nothing
- **WHEN** a mail scanner opens the unsubscribe link without submitting
- **THEN** the subscriber is still receiving the email

#### Scenario: One-click post
- **WHEN** a mail client posts to the unsubscribe address as the `List-Unsubscribe-Post` header describes, with no CSRF token
- **THEN** the subscriber is paused

#### Scenario: Altered link
- **WHEN** a post goes to an unsubscribe address whose signature was changed
- **THEN** nothing changes and the response is an error

#### Scenario: Resume
- **WHEN** a paused subscriber signs in and resumes
- **THEN** the weekly email is sent to them again

### Requirement: Privacy page and admin
The privacy page SHALL state that the site keeps an email address, the choices made and, for a "near a place" choice, the place's rounded coordinates, that Amazon SES sends the email, that opens and clicks are not tracked, and how to delete the data. It SHALL no longer say that the site keeps nothing about a visitor. Editors SHALL see subscribers in the admin with their address, confirmed and paused state and creation date, and SHALL be able to delete one.

#### Scenario: Privacy page
- **WHEN** a visitor opens the privacy page
- **THEN** it describes the weekly email's stored data and the delete-account option

#### Scenario: Admin lists subscribers
- **WHEN** an editor opens the subscribers in the admin
- **THEN** each row shows address, confirmed, paused and created date
