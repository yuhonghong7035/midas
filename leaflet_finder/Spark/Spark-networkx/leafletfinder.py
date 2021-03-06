import sys
import numpy as np
import networkx as nx
from pyspark import SparkContext
from time import time


def find_edges((window,index),cutoff=15.00):
    
    frame_list = np.zeros((len(window[0]),len(window[1])), dtype=bool)
    
    for i in range(0,len(window[0])):
        for j in range(0,len(window[1])):
            if np.sqrt(sum((window[0][i] - window[1][j]) ** 2)) <= cutoff:
                frame_list[i][j]=True

    return (frame_list,index)

if __name__=="__main__":


    if len(sys.argv) != 3:
        print "Usage: Leaflet Finder: enter <partition_size> <atom_filename>"
        exit(-1)
    else:
        part_size = int(sys.argv[1])
        filename = sys.argv[2]

    start_time = time() 
    sc = SparkContext(appName="PythonLeafletFinder")    
    
    
    coord_matrix = np.load(filename)
    matrix_size = coord_matrix.shape[0]
    #coord_matrix_broadcast = sc.broadcast(coord_matrix)
    arraged_coord = list()
    for i in range(1,matrix_size+1,part_size):
        for j in range(i,matrix_size,part_size):
            arraged_coord.append([coord_matrix[i-1:i-1+part_size],coord_matrix[j-1:j-1+part_size]])

    #Create a small matrix for positioning the sumatrices
    partition_matrix = np.zeros((matrix_size/part_size,matrix_size/part_size))
    step = 0
    for i in range(0,matrix_size/part_size):
        for j in range(i,matrix_size/part_size):
            partition_matrix[i,j] =  step + (j - i)
        step = step + (matrix_size/part_size) - i

    print len(arraged_coord)
    dist_Matrix = sc.parallelize(arraged_coord,len(arraged_coord))
    init_time = time()
    # if this RDD is use in a function keep in mind that the pair
    # (value,index) will be passed. As a result it is collected
    # with the index and becomes a list of pairs.
    # From spark docs:
    # >>> sc.parallelize(["a", "b", "c", "d"], 3).zipWithIndex().collect()
    # [('a', 0), ('b', 1), ('c', 2), ('d', 3)]
    dist_Matrix = dist_Matrix.zipWithIndex()  #key-value pairs
    #print dist_Matrix.collect()
    edge_list = dist_Matrix.map(find_edges)
    #arr = edge_list.collect()


    adj_matrix = np.zeros((matrix_size,matrix_size),dtype=bool)
    for element in edge_list.collect():
        #Find where in the result matrix the submatrix will be positioned
        pos = np.where(partition_matrix == element[1])
        #print element[1],element[0].shape, pos
        adj_matrix[pos[0][0]*part_size:((pos[0][0]+1)*part_size),pos[1][0]*part_size:((pos[1][0]+1)*part_size)] = element[0]
    
    #outfile = "adj_matrix"
    #np.save(outfile,arr)
    time_to_create_adj_matrix = time()
    #np.save('test_adj_matrix.npz.npy',adj_matrix)
    ##
    graph = nx.Graph(adj_matrix)
    subgraphs = nx.connected_components(graph)
    indices = [np.sort(list(g)) for g in subgraphs]
    np.save('components.npz.npy',indices)

    print 'Total time to create the Adjacency Matrix: %f sec'  % (time_to_create_adj_matrix - start_time)
    print 'Time to calculate the Connected Components: %f sec ' % (time() - time_to_create_adj_matrix)
    
