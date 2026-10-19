# sae_lib

- One module per area; none above about 1,000 lines. Parallel jobs collide in one big file.
- A read-only command (`sae status`, `sae next`, `sae check`, `--help`, …) takes no lock and
  writes nothing. The writing command that acts on a result stores it (`sae dispatch` records
  the next-step card). A reviewer in a read-only sandbox must be able to run them.
