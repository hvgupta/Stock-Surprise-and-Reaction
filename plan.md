# Stock Surprise and Reaction

## My understanding of the task
- For all of the companies from S&P500 whos data I am able to retrieve, which surprised market the most
    - I will define raw-surprise as: $\frac{\text{Actual EPS} - \text{Estimated EPS}}{\text{Estimated EPS}}$
    - The absolute value of it can be used to determine if it actually is a surprise ($\pm 10\%$)