$Title trnsport model using gdx files
$EOLCOM //
  Sets
       i   canning plants   / seattle, san-diego /
       j   markets          / new-york, chicago, topeka / ;

  Parameters
       a(i)  capacity of plant i in cases
         /    seattle     350
              san-diego   600  /
       b(j)  demand at market j in cases ;

  Table d(i,j)  distance in thousands of miles
                    new-york       chicago      topeka
      seattle          2.5           1.7          1.8
      san-diego        2.5           1.8          1.4 ;

  Scalar f freight in dollars per case per thousand miles /90/ ;
  
  Parameter c(i,j) transport cost in thousands of dollars per case ;

            c(i,j) = f * d(i,j) / 1000 ;

  Variables
       x(i,j)  shipment quantities in cases
       z       total transportation costs in thousands of dollars ;

  Positive Variable x ;

  Equations
       cost        define objective function
       supply(i)   observe supply limit at plant i
      demand(j)    satisfy demand at market j ;

// These lines execute during the compilation phase
// The GAMS system directory is passed to the program so it knows where
// to look for the gdxdclib library

$call 'python transport.py .'          // create demand data
$GDXIN demanddata.gdx                  // open data file
$LOAD b=demand                         // load parameter b (named 'demand' in file)
$GDXIN                                 // close data file

  cost..            z  =e=  sum((i,j), c(i,j)*x(i,j)) ;

  supply(i) ..      sum(j, x(i,j))  =l=  a(i) ;

  demand(j) ..      sum(i, x(i,j))  =g=  b(j) ;
  
  Model transport /all/ ;

  Solve transport using lp minimizing z ;

  Display b,x.l, x.m ;

// These lines execute during the execution phase
execute_unload 'results.gdx',x;                  // write variable x to the gdx file
execute 'python transport.py . results.gdx';     // do something with the solution

