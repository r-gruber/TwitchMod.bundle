Install:
-----

Put `TwitchMod.bundle` into `Plex Media Server/Plug-ins`

Preferences:
-----------
#####General Preferences
 * **Username:** The username to get followed channels for. This channel does not need your password since Twitch lets you pull this data without authenticating.
 * **Order Following By:** The ordering of the followed channels page. Ordering by views will put all online channels first.
 * **Favourite Games:** A comma separated list of games titles. Use this if you like viewing games with small amounts of viewers. Game titles dont have to be exact matches. ex: `diablo, starcraft`.
 * **Title Layout:** What info is shown in the stream title. If you don't like any of the options, please suggest some.
 * **Title Layout (game lists):** A separate title layout for lists where you know the game title going in.

#####Quality Prefrences
If you have issues getting streams to load on a particular Plex client, try the various options here.
 * **Stream Quality**, **VOD Quality**
   * *Automatic* - The client gets the master playlist. If the client supports adaptive streaming, it can make its own decisions.
   * *Manual* - For clients that allow users to select video quality (PHT).
   * *Source/High/Medium/Low/Mobile* - Explicitly use the selected quality. If the chosen quality does not exist on the chose stream, it will get the closest match.

If none of these options work, then it is likely that your client does not currently support HLS streams.

License
-------

If the software submitted to this repository accesses or calls any software provided by Plex (“Interfacing Software”), then as a condition for receiving services from Plex in response to such accesses or calls, you agree to grant and do hereby grant to Plex and its affiliates worldwide a worldwide, nonexclusive, and royalty-free right and license to use (including testing, hosting and linking to), copy, publicly perform, publicly display, reproduce in copies for distribution, and distribute the copies of any Interfacing Software made by you or with your assistance; provided, however, that you may notify Plex at legal@plex.tv if you do not wish for Plex to use, distribute, copy, publicly perform, publicly display, reproduce in copies for distribution, or distribute copies of an Interfacing Software that was created by you, and Plex will reasonable efforts to comply with such a request within a reasonable time.
