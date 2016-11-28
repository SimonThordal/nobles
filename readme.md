## A graph representation of European nobility
This project uses the genealogical information collected by Brian Tompsett over the course of what I can only assume is many years.
It includes genealogical information of more than 50.000 European noble houses with a schema representation like this:

```
Nodes:
(:Person)
(:Title)
Relationships:
(:Person)-[:child_of]->(:Person)
(:Person)-[:married_to]->(:Person)
(:Person)-[:holds_title]->(:Title)
```

Quite simple.
