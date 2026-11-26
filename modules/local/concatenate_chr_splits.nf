process concatenate_chr_splits {
    tag "$GCST"
    
    conda (params.enable_conda ? "${task.ext.conda}" : null)

    container "${ workflow.containerEngine == 'singularity' &&
        !task.ext.singularity_pull_docker_container ?
        "${task.ext.singularity}${task.ext.singularity_version}" :
        "${task.ext.docker}${task.ext.docker_version}" }"

    input:
    tuple val(GCST), val(palin_mode), path("*")

    output:
    tuple val(GCST), val(palin_mode), path ('harmonised.tsv'), emit: all_hm

    shell:
    """
    : > harmonised.tsv
    for split in *.merged.hm; do
        if [ -s "\$split" ]; then
            head -n1 "\$split" > harmonised.tsv
            break
        fi
    done
    for c in \$(seq 1 22) X Y MT; do
    if [ -f chr\$c.merged.hm ]; then
            echo chr\$c.merged.hm
            tail -n+2 chr\$c.merged.hm >> harmonised.tsv
    fi
    done
    if ! awk 'NR == 2 { found = 1; exit } END { exit !found }' harmonised.tsv; then
        echo "ERROR: $GCST has no harmonized variant rows" >&2
        exit 1
    fi
    """
}
