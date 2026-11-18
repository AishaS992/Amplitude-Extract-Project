create pipe as_des9_amplitude_snowpipe
    auto_ingest = true
                                                    -- this is setting up the pipe and adding the configurations
as

copy into raw
from (
    select
        $1
        , metadata$filename
        from @as_amplitude_stage
)
file_format = (

    type = 'JSON'
    ALLOW_DUPLICATE = false
    strip_outer_array = true
);

show pipes;

-- after doing the above, copy the notification channel value - the location that snowflake is watching for an event to occur 

select * from raw;

select system$pipe_status('as_des9_amplitude_snowpipe');

select count(*) from raw;